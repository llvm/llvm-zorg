from buildbot.steps.shell import ShellCommand
from buildbot.process.properties import WithProperties

import LLVMGCCBuilder

def getNightlytestBuildFactory(submitAux=None, *args, **kwargs):
  f = LLVMGCCBuilder.getLLVMGCCBuildFactory(*args, **kwargs)

  # Copy NT script.
  f.addStep(ShellCommand(name="cp test script", 
                         command=["cp", 
                                  WithProperties("%(builddir)s/llvm.src/utils/NewNightlyTest.pl"),
                                  "."],
                         haltOnFailure=True,
                         workdir="llvm.nt",
                         description="cp test script"))

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
                         env={ 'LLVMGCCDIR' : WithProperties("%(builddir)s/llvm-gcc.install"),
                               'BUILDDIR' : WithProperties("%(builddir)s/llvm.nt/build"), 
                               'WEBDIR' : WithProperties("%(builddir)s/llvm.nt/testresults"), 
                               },
                         haltOnFailure=True,
                         workdir="llvm.nt",
                         description="nightlytest"))
  return f
