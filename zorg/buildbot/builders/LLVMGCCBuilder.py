import buildbot
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, WarningCountingShellCommand
from buildbot.steps.shell import ShellCommand, SetProperty
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.ClangTestCommand import ClangTestCommand

def getConfigArgs(origname):
  name = origname
  args = []
  if name.startswith('Release'):
    name = name[len('Release'):]
    args.append('--enable-optimized')
  elif name.startswith('Debug'):
    name = name[len('Debug'):]
  else:
    raise ValueError,'Unknown config name: %r' % origname

  if name.startswith('-Asserts'):
    name = name[len('-Asserts'):]
    args.append('--disable-assertions')

  if name.startswith('+Checks'):
    name = name[len('+Checks'):]
    args.append('--enable-expensive-checks')

  if name:
    raise ValueError,'Unknown config name: %r' % origname

  return args

def getLLVMGCCBuildFactory(jobs=1, update=True, clean=True,
                           gxxincludedir=None, triple=None,
                           useTwoStage=True, stage1_config='Release',
                           stage2_config='Release'):
  f = buildbot.process.factory.BuildFactory()

  # Determine the build directory.
  f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                             command=["pwd"],
                                             property="builddir",
                                             description="set build dir",
                                             workdir="."))

  # Get the sources.
  if update:
    f.addStep(SVN(name='svn-llvm',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir="llvm.src"))
    f.addStep(SVN(name='svn-llvm-gcc',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm-gcc-4.2/',
                  defaultBranch='trunk',
                  workdir="llvm-gcc.src"))

  # Clean up llvm (stage 1).
  if clean:
    f.addStep(ShellCommand(name="rm-llvm.obj.stage1",
                           command=["rm", "-rf", "llvm.obj"],
                           haltOnFailure=True,
                           description=["rm build dir",
                                        "llvm",
                                        "(stage 1)"],
                           workdir="."))

  # Configure llvm (stage 1).
  base_llvm_configure_args = [WithProperties("%(builddir)s/llvm.src/configure")]
  if triple:
    base_llvm_configure_args.append('--build=' + triple)
    base_llvm_configure_args.append('--host=' + triple)
    base_llvm_configure_args.append('--target=' + triple)
  stage_configure_args = getConfigArgs(stage1_config)
  f.addStep(Configure(name='configure.llvm.stage1',
                      command=base_llvm_configure_args +
                              stage_configure_args +
                              ["--without-llvmgcc",
                               "--without-llvmgxx"],
                      description=["configure",
                                   "llvm",
                                   "(stage 1)",
                                   stage1_config],
                      workdir="llvm.obj"))

  # Build llvm (stage 1).
  f.addStep(WarningCountingShellCommand(name = "compile.llvm.stage1",
                                        command = "nice -n 10 make -j%d" % jobs,
                                        haltOnFailure = True,
                                        description=["compile",
                                                     "llvm",
                                                     "(stage 1)",
                                                     stage1_config],
                                        workdir="llvm.obj"))

  # Run LLVM tests (stage 1).
  f.addStep(ClangTestCommand(name = 'test.llvm.stage1',
                             command = ["make", "check-lit", "VERBOSE=1"],
                             description = ["testing", "llvm"],
                             descriptionDone = ["test", "llvm"],
                             workdir = 'llvm.obj'))

  # Clean up llvm-gcc.
  if clean:
    f.addStep(ShellCommand(name="rm-llvm-gcc.obj.stage1",
                           command=["rm", "-rf", "llvm-gcc.obj"],
                           haltOnFailure = True,
                           description=["rm build dir",
                                        "llvm-gcc"],
                           workdir="."))

  # Configure llvm-gcc.
  base_llvmgcc_configure_args = ["../llvm-gcc.src/configure",
                                 "--enable-languages=c,c++"]
  if gxxincludedir:
    base_llvmgcc_configure_args.append('--with-gxx-include-dir=' + gxxincludedir)
  if triple:
    base_llvmgcc_configure_args.append('--build=' + triple)
    base_llvmgcc_configure_args.append('--host=' + triple)
    base_llvmgcc_configure_args.append('--target=' + triple)
  f.addStep(Configure(name='configure.llvm-gcc.stage1',
                      command=(base_llvmgcc_configure_args +
                               ["--program-prefix=llvm-",
                                WithProperties("--prefix=%(builddir)s/llvm-gcc.install"),                      
                                WithProperties("--enable-llvm=%(builddir)s/llvm.obj")]),
                      haltOnFailure = True,
                      description=["configure",
                                   "llvm-gcc",
                                   "(stage 1)"],
                      workdir="llvm-gcc.obj"))

  # Build llvm-gcc.
  f.addStep(WarningCountingShellCommand(name="compile.llvm-gcc.stage1",
                                        command="nice -n 10 make -j%d" % jobs,
                                        haltOnFailure=True,
                                        description=["compile",
                                                     "llvm-gcc"],
                                        workdir="llvm-gcc.obj"))

  # Clean up llvm-gcc install.
  if clean:
    f.addStep(ShellCommand(name="rm-llvm-gcc.install.stage1",
                           command=["rm", "-rf", "llvm-gcc.install"],
                           haltOnFailure = True,
                           description=["rm install dir",
                                        "llvm-gcc"],
                           workdir="."))

  # Install llvm-gcc.
  f.addStep(WarningCountingShellCommand(name="install.llvm-gcc.stage1",
                                        command="nice -n 10 make install",
                                        haltOnFailure=True,
                                        description=["install",
                                                     "llvm-gcc"],
                                        workdir="llvm-gcc.obj"))

  # We are done if not doing a two-stage build.
  if not useTwoStage:
    return f

  # Clean up llvm (stage 2).
  if clean:
    f.addStep(ShellCommand(name="rm-llvm.obj.stage2",
                           command=["rm", "-rf", "llvm.obj.2"],
                           haltOnFailure=True,
                           description=["rm build dir",
                                        "llvm",
                                        "(stage 2)"],
                           workdir="."))

  # Configure llvm (stage 2).
  stage_configure_args = getConfigArgs(stage2_config)
  f.addStep(Configure(name="configure.llvm.stage2",
                      command=base_llvm_configure_args + 
                              stage_configure_args +
                              [WithProperties("--with-llvmgcc=%(builddir)s/llvm-gcc.install/bin/llvm-gcc"),
                               WithProperties("--with-llvmgxx=%(builddir)s/llvm-gcc.install/bin/llvm-g++")],
                      env={'CC' : WithProperties("%(builddir)s/llvm-gcc.install/bin/llvm-gcc"),
                           'CXX' :  WithProperties("%(builddir)s/llvm-gcc.install/bin/llvm-g++"),},
                      haltOnFailure=True,
                      workdir="llvm.obj.2",
                      description=["configure",
                                   "llvm",
                                   "(stage 2)",
                                   stage2_config]))

  # Build LLVM (stage 2).
  f.addStep(WarningCountingShellCommand(name = "compile.llvm.stage2",
                                        command = "nice -n 10 make -j%d" % jobs,
                                        haltOnFailure = True,
                                        description=["compile",
                                                     "llvm",
                                                     "(stage 2)",
                                                     stage2_config],
                                        workdir="llvm.obj.2"))

  # Run LLVM tests (stage 2).
  f.addStep(ClangTestCommand(name = 'test.llvm.stage2',
                             command = ["make", "check-lit", "VERBOSE=1"],
                             description = ["testing", "llvm", "(stage 2)"],
                             descriptionDone = ["test", "llvm", "(stage 2)"],
                             workdir = 'llvm.obj.2'))

  # Clean up llvm-gcc (stage 2).
  if clean:
    f.addStep(ShellCommand(name="rm-llvm-gcc.obj.stage2",
                           command=["rm", "-rf", "llvm-gcc.obj.2"],
                           haltOnFailure = True,
                           description=["rm build dir",
                                        "llvm-gcc",
                                        "(stage 2)"],
                           workdir="."))

  # Configure llvm-gcc (stage 2).
  f.addStep(Configure(name = 'configure.llvm-gcc.stage2',
                      command=base_llvmgcc_configure_args + [
                               "--program-prefix=llvm.2-",
                               WithProperties("--prefix=%(builddir)s/llvm-gcc.install.2"),
                               WithProperties("--enable-llvm=%(builddir)s/llvm.obj.2")],
                      env={'CC' : WithProperties("%(builddir)s/llvm-gcc.install/bin/llvm-gcc"),
                           'CXX' :  WithProperties("%(builddir)s/llvm-gcc.install/bin/llvm-g++"),},
                      haltOnFailure = True,
                      description=["configure",
                                   "llvm-gcc",
                                   "(stage 2)"],
                      workdir="llvm-gcc.obj.2"))

  # Build llvm-gcc (stage 2).
  f.addStep(WarningCountingShellCommand(name="compile.llvm-gcc.stage2",
                                        command="nice -n 10 make -j%d" % jobs,
                                        haltOnFailure=True,
                                        description=["compile",
                                                     "llvm-gcc",
                                                     "(stage 2)"],
                                        workdir="llvm-gcc.obj.2"))

  # Clean up llvm-gcc install (stage 2).
  if clean:
    f.addStep(ShellCommand(name="rm-llvm-gcc.install.stage2",
                           command=["rm", "-rf", "llvm-gcc.install.2"],
                           haltOnFailure = True,
                           description=["rm install dir",
                                        "llvm-gcc",
                                        "(stage 2)"],
                           workdir="."))

  # Install llvm-gcc.
  f.addStep(WarningCountingShellCommand(name="install.llvm-gcc.stage2",
                                        command="nice -n 10 make",
                                        haltOnFailure=True,
                                        description=["install",
                                                     "llvm-gcc",
                                                     "(stage 2)"],
                                        workdir="llvm-gcc.obj.2"))

  return f

