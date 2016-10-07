from buildbot.steps.slave import RemoveDirectory
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand
from zorg.buildbot.commands.MakeCommand  import MakeCommand

from zorg.buildbot.conditions.FileConditions import FileDoesNotExist
from zorg.buildbot.process.factory import LLVMBuildFactory

def getCmakeBuildFactory(
           depends_on_projects = None,
           llvm_srcdir = None,
           obj_dir = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           env = None,
           **kwargs):

    # Set defaults
    if not depends_on_projects:
        depends_on_projects=['llvm', 'clang']

    if extra_configure_args is None:
        extra_configure_args = []

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Be cautious and disable color output from all tools.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    if not obj_dir:
        obj_dir = "build"

    if install_dir:
        install_dir_rel = LLVMBuildFactory.pathRelativeToBuild(
                              install_dir,
                              obj_dir)
        CmakeCommand.applyRequiredOptions(extra_configure_args, [
            ('-DCMAKE_INSTALL_PREFIX=', install_dir_rel),
            ])

    cleanBuildRequested = lambda step: step.build.getProperty("clean") or clean

    f = LLVMBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir or "llvm.src",
            obj_dir=obj_dir,
            install_dir=install_dir,
            cleanBuildRequested=cleanBuildRequested,
            **kwargs # Pass through all the extra arguments.
            )

    # Directories to use on this stage.
    src_dir = LLVMBuildFactory.pathRelativeToBuild(f.llvm_srcdir, obj_dir)

    # Do a clean checkout if requested.
    f.addStep(RemoveDirectory(name='clean-src-dir',
              dir=f.llvm_srcdir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested,
              ))

    # Get the source code.
    f.addSVNSteps()

    # This is an incremental build, unless otherwise has been requested.
    # Remove obj and install dirs for a clean build.
    f.addStep(RemoveDirectory(name='clean-%s-dir' % f.obj_dir,
              dir=f.obj_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested,
              ))

    if f.install_dir:
        f.addStep(RemoveDirectory(name='clean-%s-dir' % f.install_dir,
              dir=f.install_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested,
              ))

    # Reconcile the cmake options for this build.

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    # Set proper defaults.
    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-DCMAKE_BUILD_TYPE=',        'Release'),
        ('-DCLANG_BUILD_EXAMPLES=',    'OFF'),
        ('-DLLVM_BUILD_TESTS=',        'ON'),
        ('-DLLVM_ENABLE_ASSERTIONS=',  'ON'),
        ('-DLLVM_OPTIMIZED_TABLEGEN=', 'ON'),
        ])

    # Create configuration files with cmake, unless this has been already done
    # for an incremental build.
    f.addStep(CmakeCommand(name="cmake-configure",
                           description=["cmake configure"],
                           haltOnFailure=True,
                           options=cmake_args,
                           path=src_dir,
                           env=env,
                           workdir=obj_dir,
                           doStepIf=FileDoesNotExist("CMakeCache.txt"),
                           **kwargs # Pass through all the extra arguments.
                           ))

    return f

def getCmakeWithNinjaBuildFactory(
           depends_on_projects=None,
           llvm_srcdir=None,
           obj_dir = None,
           install_dir=None,
           clean = False,
           extra_configure_args = None,
           env = None,
           **kwargs):

    # Reconcile the cmake options for this build.

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    # To set proper defaults, uncomment and modify the following lines.
    #CmakeCommand.applyDefaultOptions(cmake_args, [
    #    ('-DCMAKE_BUILD_TYPE=',        'Release'),
    #    ])

    # Some options are required for this build no matter what.
    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-G',                      'Ninja'),
        ])

    f = getCmakeBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir or "install",
            extra_configure_args=cmake_args,
            env=env,
            **kwargs # Pass through all the extra arguments.
            )
 
    # Directories to use for this build.
    # obj_dir = f.obj_dir
    # src_dir = LLVMBuildFactory.pathRelativeToBuild(f.llvm_srcdir, obj_dir)
    # install_dir = LLVMBuildFactory.pathRelativeToBuild(f.install_dir, obj_dir)

    # Build the unified tree.
    f.addStep(NinjaCommand(name="build-unified-tree",
                           haltOnFailure=True,
                           description=["build unified tree"],
                           env=env,
                           workdir=f.obj_dir,
                           **kwargs # Pass through all the extra arguments.
                           ))

    # Test just built components
    f.addStep(NinjaCommand(name="test-check-all",
                           targets=["check-all"],
                           haltOnFailure=True,
                           description=["test just built components"],
                           env=env,
                           workdir=f.obj_dir,
                           **kwargs # Pass through all the extra arguments.
                           ))

    # Install just built components
    f.addStep(NinjaCommand(name="install-all",
                           targets=["install"],
                           haltOnFailure=True,
                           description=["install just built components"],
                           env=env,
                           workdir=f.obj_dir,
                           **kwargs # Pass through all the extra arguments.
                           ))

    return f


from buildbot.steps.shell import ShellCommand

def getCmakeWithMakeBuildFactory(
           depends_on_projects=None,
           llvm_srcdir=None,
           obj_dir = None,
           install_dir=None,
           clean = False,
           jobs  = None,
           extra_configure_args = None,
           env = None,
           **kwargs):

    # Reconcile the cmake options for this build.

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    # Set proper defaults.
    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-DCMAKE_COLOR_MAKEFILE=',    'OFF'),
        ])

    # Some options are required for this build no matter what.
    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-G',                      'Unix Makefiles'),
        ])

    f = getCmakeBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir or "install",
            extra_configure_args=cmake_args,
            env=env,
            **kwargs # Pass through all the extra arguments.
            )
 
    # Directories to use for this build.
    # obj_dir = f.obj_dir
    # src_dir = LLVMBuildFactory.pathRelativeToBuild(f.llvm_srcdir, obj_dir)
    # install_dir = LLVMBuildFactory.pathRelativeToBuild(f.install_dir, obj_dir)

    # Build the unified tree.
    f.addStep(MakeCommand(name="build-unified-tree",
                          options=["-k"],
                          haltOnFailure=True,
                          description=["build unified tree"],
                          env=env,
                          workdir=f.obj_dir,
                          **kwargs # Pass through all the extra arguments.
                         ))

    # Test just built components
    f.addStep(MakeCommand(name="check-all",
                          targets=["check-all"],
                          haltOnFailure=True,
                          description=["test just built components"],
                          env=env,
                          workdir=f.obj_dir,
                          **kwargs # Pass through all the extra arguments.
                          ))

    # Install just built components
    f.addStep(MakeCommand(name="install-all",
                          targets=["install"],
                          haltOnFailure=True,
                          description=["install just built components"],
                          env=env,
                          workdir=f.obj_dir,
                          **kwargs # Pass through all the extra arguments.
                          ))

    return f
