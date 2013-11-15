from buildbot.steps.shell import Configure, ShellCommand
from buildbot.process.properties import WithProperties
from buildbot.steps.source import SVN

from zorg.buildbot.commands.NightlyTestCommand import NightlyTestCommand

import LLVMGCCBuilder
import ClangBuilder

def getNightlytestBuildFactory(submitAux=None, *args, **kwargs):
  f = LLVMGCCBuilder.getLLVMGCCBuildFactory(*args, **kwargs)

  # Prepare environmental variables. Set here all env we want everywhere.
  merged_env = {
                   'TERM' : 'dumb'     # Make sure Clang doesn't use color escape sequences.
               }

  env = kwargs.pop('env', None)
  if env is not None:
      merged_env.update(env)  # Overwrite pre-set items with the given ones, so user can set anything.

  # Copy NT script.
  f.addStep(ShellCommand(name="cp test script", 
                         command=["cp", 
                                  WithProperties("%(builddir)s/llvm.src/utils/NewNightlyTest.pl"),
                                  "."],
                         haltOnFailure = True,
                         description   = "cp test script",
                         workdir       = "llvm.nt",
                         env           = merged_env))

  submitCommand = []
  if submitAux is not None:
      submitCommand = ['-submit-aux',
                       submitAux]

  f.addStep(ShellCommand(name="nightlytest", 
                         command=["./NewNightlyTest.pl",
                                  "-parallel-jobs", WithProperties("%(jobs)s"), 
                                  "-parallel",
                                  "-noremoveatend",
                                  "-noremoveresults",
                                  "-release",
                                  "-enable-llcbeta",
                                  "-verbose",
                                  "-nickname", WithProperties("%(slavename)s"),
                                  "-test-cxxflags", "-I/usr/include/c++/4.2.1/i686-apple-darwin10 -I/usr/include/c++/4.2.1",
                                  "-nosubmit",
                                  "-teelogs"] + submitCommand,
                         haltOnFailure = True,
                         description   = "nightlytest",
                         workdir       = "llvm.nt",
                         env           = {
                                          'LLVMGCCDIR' : WithProperties("%(builddir)s/llvm-gcc.install"),
                                          'BUILDDIR'   : WithProperties("%(builddir)s/llvm.nt/build"),
                                          'WEBDIR'     : WithProperties("%(builddir)s/llvm.nt/testresults"),
                                         }.update(merged_env)))
  return f

def getFastNightlyTestBuildFactory(triple, xfails=[], clean=True, test=False, make='make', **kwargs):
  # Build compiler to test.  
  f = ClangBuilder.getClangBuildFactory(
    triple, outOfDir=True, clean=clean, test=test,
    make=make, **kwargs)

  # Prepare environmental variables. Set here all env we want everywhere.
  merged_env = {
                   'TERM' : 'dumb'     # Make sure Clang doesn't use color escape sequences.
               }
  env = kwargs.pop('env', None)
  if env is not None:
      merged_env.update(env)  # Overwrite pre-set items with the given ones, so user can set anything.

  # Get the test-suite sources.
  f.addStep(SVN(name          = 'svn-test-suite',
                mode          = 'update',
                baseURL       = 'http://llvm.org/svn/llvm-project/test-suite/',
                defaultBranch = 'trunk',
                workdir       = 'test-suite.src'))

  # Clean up.
  if clean:
      f.addStep(ShellCommand(name="rm.test-suite",
                             command=["rm", "-rf", "test-suite.obj"],
                             haltOnFailure = True,
                             description   = "rm test-suite build dir",
                             workdir       = ".",
                             env           = merged_env))

  # Configure.
  f.addStep(Configure(name="configure.test-suite",
                      command=['../test-suite.src/configure',
                               WithProperties("--with-llvmsrc=%(builddir)s/llvm.src"),
                               WithProperties("--with-llvmobj=%(builddir)s/llvm.obj"),
                               WithProperties("--with-built-clang")],
                      haltOnFailure   = True,
                      description     = ["configuring", "test-suite"],
                      descriptionDone = ["configure",   "test-suite"],
                      workdir         = 'test-suite.obj',
                      env             = merged_env))

  # Build and test.
  f.addStep(ShellCommand(name="rm.test-suite.report",
                         command=["rm", "-rf",
                                  "test-suite.obj/report.nightly.raw.out",
                                  "test-suite.obj/report.nightly.txt"],
                         haltOnFailure = True,
                         description   = "rm test-suite report",
                         workdir       = ".",
                         env           = merged_env))
  f.addStep(NightlyTestCommand(name="make.test-suite",
                               command=[make, WithProperties("-j%(jobs)s"),
                                        "ENABLE_PARALLEL_REPORT=1",
                                        "DISABLE_CBE=1", "DISABLE_JIT=1",
                                        "TEST=nightly", "report"],
                               haltOnFailure   = True,
                               logfiles        = { 'report' : 'report.nightly.txt' },
                               xfails          = xfails,
                               description     = ["running", "test-suite"],
                               descriptionDone = ["run",     "test-suite"],
                               workdir         = 'test-suite.obj',
                               env             = merged_env))

  return f
