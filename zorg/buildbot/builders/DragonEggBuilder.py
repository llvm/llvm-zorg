import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.process.properties import WithProperties

def getBuildFactory(triple, clean=True,
                    jobs='%(jobs)s'):
    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir="."))

    # Checkout LLVM sources.
    f.addStep(SVN(name='svn-llvm',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir='llvm.src'))

    # Checkout DragonEgg sources.
    f.addStep(SVN(name='svn-dragonegg',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/dragonegg/',
                  defaultBranch='trunk',
                  workdir='dragonegg.src'))

    # Execute the DragonEgg self host script.
    f.addStep(ShellCommand(name='build',
                           command=['dragonegg.src/extras/buildbot_self_strap',
                                    # Path to LLVM src.
                                    WithProperties("%(builddir)s/llvm.src"),
                                    # Path to DragonEgg src.
                                    WithProperties("%(builddir)s/dragonegg.src"),
                                    # Path to base build dir.
                                    WithProperties("%(builddir)s")],
                           workdir='.',
                           haltOnFailure=False))

    return f

# This is the sketching of a more buildbot style build factory for
# DragonEgg, but it is far from complete.
def getBuildFactory_Split(triple, clean=True,
                          jobs='%(jobs)s'):
    # FIXME: Move out.
    env = {}
    configure_args = ["--enable-lto", "--enable-languages=c,c++", "--disable-bootstrap",
                      "--disable-multilib", "--enable-checking", 
                      "--with-mpfr=/opt/cfarm/mpfr-2.4.1", "--with-gmp=/opt/cfarm/gmp-4.2.4",
                      "--with-mpc=/opt/cfarm/mpc-0.8", "--with-libelf=/opt/cfarm/libelf-0.8.12"]

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir="."))

    # Checkout LLVM sources.
    f.addStep(SVN(name='svn-llvm',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir='llvm.src'))

    # Checkout DragonEgg sources.
    f.addStep(SVN(name='svn-dragonegg',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/dragonegg/',
                  defaultBranch='trunk',
                  workdir='dragonegg.src'))

    # Revert any DragonEgg patches.
    f.addStep(ShellCommand(name='patch.revert.gcc',
                           command=['svn','revert','-R','gcc'],
                           workdir='gcc.src',
                           haltOnFailure=False))

    # Checkout GCC sources.
    #
    # FIXME: This is going to mess up revision numbers.
    f.addStep(SVN(name='svn-gcc',
                  mode='update', baseURL='svn://gcc.gnu.org/svn/gcc/',
                  defaultBranch='trunk',
                  workdir='gcc.src'))

    # Apply patch.
    #
    # FIXME: Eliminate this.
    f.addStep(ShellCommand(name='patch.gcc',
                           command="patch -p1 < ../dragonegg.src/gcc-patches/i386_static.diff",
                           workdir='gcc.src'))

    # Build and install GCC.
    if clean:
        f.addStep(ShellCommand(name="rm-gcc.obj.stage1",
                               command=["rm", "-rf", "gcc.1.obj"],
                               haltOnFailure = True,
                               description=["rm build dir", "gcc"],
                               workdir=".", env=env))
    # Create the gcc.1.obj dir. FIXME: This shouldn't be necessary, old buildbot or something.
    f.addStep(ShellCommand(command="mkdir gcc.1.obj",
                           workdir='.'))
    f.addStep(Configure(name='configure.gcc.stage1',
                        command=(["../gcc.src/configure",
                                  WithProperties("--prefix=%(builddir)s/gcc.1.install")] +
                                 configure_args),
                        haltOnFailure = True,
                        description=["configure", "gcc", "(stage 1)"],
                        workdir="gcc.1.obj", env=env))
    f.addStep(WarningCountingShellCommand(name = "compile.gcc.stage1",
                                          command = ["nice", "-n", "10",
                                                     "make", WithProperties("-j%s" % jobs)],
                                          haltOnFailure = True,
                                          description=["compile", "gcc", "(stage 1)"],
                                          workdir="gcc.1.obj", env=env))
    f.addStep(WarningCountingShellCommand(name = "install.gcc.stage1",
                                          command = ["nice", "-n", "10",
                                                     "make", "install"],
                                          haltOnFailure = True,
                                          description=["install", "gcc", "(stage 1)"],
                                          workdir="gcc.1.obj", env=env))

    # Build LLVM (stage 1) with the GCC (stage 1).
    if clean:
        f.addStep(ShellCommand(name="rm-llvm.obj.stage1",
                               command=["rm", "-rf", "llvm.1.obj"],
                               haltOnFailure = True,
                               description=["rm build dir", "llvm"],
                               workdir=".", env=env))
    # Create the llvm.1.obj dir. FIXME: This shouldn't be necessary, old buildbot or something.
    f.addStep(ShellCommand(command="mkdir llvm.1.obj",
                           workdir='.'))
    f.addStep(Configure(name='configure.llvm.stage1',
                        command=(["../llvm.src/configure",
                                  WithProperties("CC=%(builddir)s/gcc.1.install/bin/gcc"),
                                  WithProperties("CXX=%(builddir)s/gcc.1.install/bin/g++"),
                                  WithProperties("--prefix=%(builddir)s/llvm.1.install"),
                                  "--enable-optimized",
                                  "--enable-assertions"] +
                                 configure_args),
                        haltOnFailure = True,
                        description=["configure", "llvm", "(stage 1)"],
                        workdir="llvm.1.obj", env=env))
    f.addStep(WarningCountingShellCommand(name = "compile.llvm.stage1",
                                          command = ["nice", "-n", "10",
                                                     "make", WithProperties("-j%s" % jobs)],
                                          haltOnFailure = True,
                                          description=["compile", "llvm", "(stage 1)"],
                                          workdir="llvm.1.obj", env=env))
    f.addStep(WarningCountingShellCommand(name = "install.llvm.stage1",
                                          command = ["nice", "-n", "10",
                                                     "make", WithProperties("-j%s" % jobs),
                                                     "install"],
                                          haltOnFailure = True,
                                          description=["install", "llvm", "(stage 1)"],
                                          workdir="llvm.1.obj", env=env))

    # Clean DragonEgg.
    if clean:
        f.addStep(ShellCommand(name="clean.dragonegg.stage1",
                               command=["make", "clean"],
                               haltOnFailure = True,
                               description=["make clean",
                                            "(dragonegg)"],
                               workdir="dragonegg.src", env=env))
    local_env = env.copy()
    # Don't do a version check, which may fail based on timestamps.
    local_env['dragonegg_disable_version_check'] = "yes"
    f.addStep(WarningCountingShellCommand(
            name = "compile.dragonegg.stage1",
            command = ["nice", "-n", "10",
                       "make", WithProperties("-j%s" % jobs),
                       "CFLAGS=-I/opt/cfarm/mpfr-2.4.1/include -I/opt/cfarm/gmp-4.2.4/include/ -I/opt/cfarm/mpc-0.8/include/",
                       WithProperties("CC=%(builddir)s/gcc.1.install/bin/gcc"),
                       WithProperties("CXX=%(builddir)s/gcc.1.install/bin/g++"),
                       WithProperties("GCC=%(builddir)s/gcc.1.install/bin/gcc"),
                       WithProperties("LLVM_CONFIG=%(builddir)s/llvm.1.obj/Debug/bin/llvm-config"),
                       ],
            haltOnFailure = True,
            description=["compile", "dragonegg", "(stage 1)"],
            workdir="dragonegg.src", env=env))
    
    return f

