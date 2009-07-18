import buildbot
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, WarningCountingShellCommand
from buildbot.steps.shell import ShellCommand, SetProperty
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.DejaGNUCommand import DejaGNUCommand
from zorg.buildbot.commands.GTestCommand import GTestCommand

def getLLVMGCCBuildFactory(checkoutLLVMTest=False):
  f = buildbot.process.factory.BuildFactory()

  # Determine the build directory.
  f.addStep(SetProperty(name="get_builddir", command=["pwd"], property="builddir",
                        description="set build dir",
                        workdir="."))

  # Clean up.
  if True:
    f.addStep(ShellCommand(name="remove llvm build",
                           command=["rm", "-rf", "llvm.obj"],
                           haltOnFailure=True,
                           description="rm llvm build dir",
                           workdir="."))
    f.addStep(ShellCommand(name="remove llvm install",
                           command=["rm", "-rf", "llvm.install"],
                           haltOnFailure=True,
                           description="rm llvm install dir",
                           workdir="."))
    f.addStep(ShellCommand(name="remove llvm-gcc build",
                           command=["rm", "-rf", "llvm-gcc.obj"],
                           haltOnFailure=True,
                           description="rm llvm-gcc build dir",
                           workdir="."))
    f.addStep(ShellCommand(name="remove llvm-gcc install",
                           command=["rm", "-rf", "llvm-gcc.install"],
                           haltOnFailure=True,
                           description="rm llvm-gcc install dir",
                           workdir="."))

  # Reset svn directories.
  f.addStep(ShellCommand(name="revert llvm",
                         command=["svn", "revert", "-R", "llvm.src"],
                         haltOnFailure=False,
                         description="revert llvm src dir",
                         workdir="."))
  f.addStep(ShellCommand(name="revert llvm-gcc",
                         command=["svn", "revert", "-R", "llvm-gcc.src"],
                         haltOnFailure=False,
                         description="revert llvm-gcc src dir",
                         workdir="."))
  if checkoutLLVMTest:
    f.addStep(ShellCommand(name="revert llvm-test",
                           command=["svn", "revert", "-R", "llvm.src/projects/llvm-test"],
                           haltOnFailure=False,
                           description="revert llvm-gcc src dir",
                           workdir="."))
  
  # Get the sources.
  f.addStep(SVN(name='svn-llvm',
                mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/', 
                defaultBranch='trunk',
                workdir="llvm.src"))
  f.addStep(SVN(name='svn-llvm-gcc',
                mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm-gcc-4.2/', 
                defaultBranch='trunk',
                workdir="llvm-gcc.src"))
  if checkoutLLVMTest:
    f.addStep(SVN(name='svn-llvm-test',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/test-suite/', 
                  defaultBranch='trunk',
                  workdir="llvm.src/projects/llvm-test"))

  # Configure, build, and install LLVM.
  f.addStep(Configure(name="configure llvm",
                      command=[WithProperties("%(builddir)s/llvm.src/configure"),
                               WithProperties("--prefix=%(builddir)s/llvm.install"),
                               "--enable-optimized"],
                      haltOnFailure=True,
                      workdir="llvm.obj",
                      description=['configuring llvm', 'Release'],
                      descriptionDone=['configure llvm', 'Release']))
  f.addStep(WarningCountingShellCommand(name="compile llvm", 
                                        command=WithProperties("make -j%(jobs)d"), 
                                        haltOnFailure=True, 
                                        description="compiling(llvm)", 
                                        descriptionDone="compile(llvm)",
                                        workdir=WithProperties("%(builddir)s/llvm.obj")))
  f.addStep(ShellCommand(name="install llvm", 
                         command=WithProperties("make -j%(jobs)d install"), 
                         haltOnFailure=True, 
                         description="installing(llvm)", 
                         descriptionDone="install(llvm)",
                         workdir=WithProperties("%(builddir)s/llvm.obj")))

  # Configure, build, and install llvm-gcc.
  f.addStep(Configure(name="configure llvm-gcc",
                      command=[WithProperties("%(builddir)s/llvm-gcc.src/configure"),
                               WithProperties("--prefix=%(builddir)s/llvm-gcc.install"),
                               "--enable-optimized",
                               WithProperties("--enable-llvm=%(builddir)s/llvm.obj"),
                               "--enable-languages=c,c++,objc,obj-c++"],
                      haltOnFailure=True,
                      workdir=WithProperties("%(builddir)s/llvm-gcc.obj"),
                      description=['configuring llvm-gcc'],
                      descriptionDone=['configure llvm-gcc']))
  f.addStep(WarningCountingShellCommand(name="compile llvm-gcc", 
                                        command=WithProperties("make -j%(jobs)d VERBOSE=1"), 
                                        haltOnFailure=True, 
                                        description="compiling(llvm-gcc)", 
                                        descriptionDone="compile(llvm-gcc)",
                                        workdir=WithProperties("%(builddir)s/llvm-gcc.obj")))
  f.addStep(ShellCommand(name="install llvm-gcc", 
                         command=WithProperties("make install"), 
                         haltOnFailure=True, 
                         description="installing(llvm-gcc)", 
                         descriptionDone="install(llvm-gcc)",
                         workdir=WithProperties("%(builddir)s/llvm-gcc.obj")))

  # Symlink for libstdc++.
  f.addStep(ShellCommand(name="ln-stdc++", 
                         command=["ln", "-sf",
                                  WithProperties("/usr/lib/libstdc++.6.dylib"),
                                  WithProperties("%(builddir)s/llvm-gcc.install/lib/")],
                         haltOnFailure=True,
                         workdir="."))
  f.addStep(ShellCommand(name="ln-gcc", 
                         command=["ln", "-sf",
                                  WithProperties("%(builddir)s/llvm-gcc.install/bin/gcc"),
                                  WithProperties("%(builddir)s/llvm-gcc.install/bin/llvm-gcc")],
                         haltOnFailure=True,
                         workdir="."))
  f.addStep(ShellCommand(name="ln-g++", 
                         command=["ln", "-sf",
                                  WithProperties("%(builddir)s/llvm-gcc.install/bin/g++"),
                                  WithProperties("%(builddir)s/llvm-gcc.install/bin/llvm-g++")],
                         haltOnFailure=True,
                         workdir="."))

  # Reconfigure to pick up our fresh llvm-gcc.
  f.addStep(Configure(name="reconfigure llvm",
                      command=[WithProperties("%(builddir)s/llvm.src/configure"),
                               WithProperties("--prefix=%(builddir)s/llvm.install"),
                               "--enable-optimized",
                               WithProperties("--with-llvmgccdir=%(builddir)s/llvm-gcc.install")],
                      haltOnFailure=True,
                      workdir=WithProperties("%(builddir)s/llvm.obj"),
                      description=['reconfiguring llvm', 'Release'],
                      descriptionDone=['reconfigure llvm', 'Release']))

  # FIXME: These includes are machine specific, should be a parameter.
  f.addStep(DejaGNUCommand(name='test-llvm',
                           command=["make", "check",
                                    "EXTRA_OPTIONS=-fstrict-aliasing -Wstrict-aliasing -I/usr/include/c++/4.0.0/i686-apple-darwin9 -I/usr/include/c++/4.0.0",
                                    "IGNORE_TESTS=ocaml.exp llvm2cpp.exp llvmc.exp"],
                           description="dejagnu (llvm)", 
                           workdir='llvm.obj'))

  f.addStep(GTestCommand(name="unittest-llvm", 
                         command=["make", "unittests"],
                         description="unittests (llvm)", 
                         workdir="llvm.obj"))
  return f

