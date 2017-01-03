from buildbot.steps.slave import RemoveDirectory
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand

from zorg.buildbot.conditions.FileConditions import FileDoesNotExist
from zorg.buildbot.process.factory import LLVMBuildFactory

def getLLVMBuildFactoryAndSVNSteps(
           depends_on_projects = None,
           llvm_srcdir = None,
           obj_dir = None,
           install_dir = None,
           cleanBuildRequested = None,
           env = None,
           **kwargs):

    # Set defaults
    if not depends_on_projects:
        depends_on_projects=['llvm', 'clang']

    if cleanBuildRequested is None:
        cleanBuildRequested = lambda step: step.build.getProperty("clean")

    f = LLVMBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir or "llvm",
            obj_dir=obj_dir or "build",
            install_dir=install_dir,
            cleanBuildRequested=cleanBuildRequested,
            **kwargs) # Pass through all the extra arguments.

    # Do a clean checkout if requested.
    # TODO: Some Windows slaves do not handle RemoveDirectory command well.
    # So, consider running "rmdir /S /Q <dir>" if the build runs on Windows.
    f.addStep(RemoveDirectory(name='clean-src-dir',
              dir=f.llvm_srcdir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested,
              ))

    # Get the source code.
    f.addSVNSteps()

    return f

def addCmakeSteps(
           f,
           cleanBuildRequested,
           obj_dir,
           install_dir = None,
           extra_configure_args = None,
           env = None,
           stage_name = None,
           **kwargs):

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    # This is an incremental build, unless otherwise has been requested.
    # Remove obj and install dirs for a clean build.
    # TODO: Some Windows slaves do not handle RemoveDirectory command well.
    # So, consider running "rmdir /S /Q <dir>" if the build runs on Windows.
    f.addStep(RemoveDirectory(name='clean-%s-dir' % obj_dir,
              dir=obj_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested,
              ))

    if install_dir:
        install_dir_rel = LLVMBuildFactory.pathRelativeToBuild(
                              install_dir,
                              obj_dir)
        CmakeCommand.applyRequiredOptions(cmake_args, [
            ('-DCMAKE_INSTALL_PREFIX=', install_dir_rel),
            ])

        f.addStep(RemoveDirectory(name='clean-%s-dir' % install_dir,
              dir=install_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested,
              ))

    # Reconcile the cmake options for this build.

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
    if stage_name:
        step_name = "cmake-configure-%s" % stage_name
    else:
        step_name = "cmake-configure"

    src_dir = LLVMBuildFactory.pathRelativeToBuild(f.llvm_srcdir, obj_dir)

    f.addStep(CmakeCommand(name=step_name,
                           description=["Cmake", "configure", stage_name],
                           haltOnFailure=True,
                           options=cmake_args,
                           path=src_dir,
                           env=env,
                           workdir=obj_dir,
                           doStepIf=FileDoesNotExist("CMakeCache.txt"),
                           **kwargs # Pass through all the extra arguments.
                           ))

def addNinjaSteps(
           f,
           obj_dir = None,
           env = None,
           stage_name = None,
           **kwargs):

    # Build the unified tree.
    if stage_name:
        step_name = "%s-" % stage_name
    else:
        step_name = ""

    if obj_dir is None:
        obj_dir = f.obj_dir

    f.addStep(NinjaCommand(name="build-%sunified-tree" % step_name,
                           haltOnFailure=True,
                           description=["Build", stage_name, "unified", "tree"],
                           env=env,
                           workdir=obj_dir,
                           **kwargs # Pass through all the extra arguments.
                           ))

    # Test just built components
    f.addStep(NinjaCommand(name="test-%scheck-all" % step_name,
                           targets=["check-all"],
                           haltOnFailure=True,
                           description=["Test", "just", "built", "components"],
                           env=env,
                           workdir=obj_dir,
                           **kwargs # Pass through all the extra arguments.
                           ))

    # Install just built components
    f.addStep(NinjaCommand(name="install-%sall" % step_name,
                           targets=["install"],
                           haltOnFailure=True,
                           description=["Install", "just", "built", "components"],
                           env=env,
                           workdir=obj_dir,
                           **kwargs # Pass through all the extra arguments.
                           ))

def getCmakeBuildFactory(
           depends_on_projects = None,
           llvm_srcdir = None,
           obj_dir = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           env = None,
           **kwargs):

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Be cautious and disable color output from all tools.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    cleanBuildRequested = lambda step: step.build.getProperty("clean") or clean

    f = getLLVMBuildFactoryAndSVNSteps(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            cleanBuildRequested=cleanBuildRequested,
            **kwargs) # Pass through all the extra arguments.

    addCmakeSteps(
        f,
        cleanBuildRequested=cleanBuildRequested,
        obj_dir=f.obj_dir,
        install_dir=f.install_dir,
        extra_configure_args=extra_configure_args,
        env=env,
        **kwargs)

    return f

def getCmakeWithNinjaBuildFactory(
           depends_on_projects = None,
           llvm_srcdir = None,
           obj_dir = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           env = None,
           **kwargs):

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    # Some options are required for this build no matter what.
    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-G',                      'Ninja'),
        ])

    f = getCmakeBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            clean=clean,
            extra_configure_args=cmake_args,
            env=env,
            **kwargs) # Pass through all the extra arguments.

    addNinjaSteps(
           f,
           obj_dir=obj_dir,
           env=env,
           **kwargs)

    return f

def getCmakeWithNinjaMultistageBuildFactory(
           depends_on_projects = None,
           llvm_srcdir = None,
           obj_dir = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           env = None,
           stages=2,
           stage_names=None,
           **kwargs):

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Be cautious and disable color output from all tools.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    assert stages > 1, "It should be at least 2 stages in a multistage build."
    if stage_names is None:
        stage_names = list()
        for i in range(1, stages + 1):
            stage_names.append("stage%s" % i)
    else:
        assert len(stage_names) == stages, "Please specify names for none or all of the requested stages."

    if obj_dir is None:
        obj_dir = "build"
    if install_dir is None:
        install_dir = "install"

    stage_objdirs = list()
    stage_installdirs = list()
    for s in stage_names:
        stage_objdirs.append("%s/%s" % (obj_dir, s))
        stage_installdirs.append("%s/%s" % (install_dir, s))

    cleanBuildRequested = lambda step: step.build.getProperty("clean") or clean

    f = getLLVMBuildFactoryAndSVNSteps(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            cleanBuildRequested=cleanBuildRequested,
            env=env,
            stage_objdirs=stage_objdirs,
            stage_installdirs=stage_installdirs,
            stage_names=stage_names,
            **kwargs) # Pass through all the extra arguments.

    # Set proper defaults.
    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-DCMAKE_BUILD_TYPE=',        'Release'),
        ('-DCLANG_BUILD_EXAMPLES=',    'OFF'),
        ('-DLLVM_BUILD_TESTS=',        'ON'),
        ('-DLLVM_ENABLE_ASSERTIONS=',  'OFF'),
        ('-DLLVM_OPTIMIZED_TABLEGEN=', 'ON'),
        ])

    # Some options are required for this build no matter what.
    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-G',                         'Ninja'),
        ])

    # The stage 1 is special, though. We use the system compiler and
    # do incremental build, unless a clean one has been requested.
    cmake_args_stage1 = cmake_args[:]
    CmakeCommand.applyDefaultOptions(cmake_args_stage1, [
        # Do not expect warning free build by the system toolchain.
        ('-DLLVM_ENABLE_WERROR=',      'OFF'),
        ])

    addCmakeSteps(
           f,
           f.cleanBuildRequested,
           obj_dir=stage_objdirs[0],
           install_dir=stage_installdirs[0],
           extra_configure_args=cmake_args_stage1,
           env=env,
           stage_name=stage_names[0],
           **kwargs)

    addNinjaSteps(
           f,
           obj_dir=stage_objdirs[0],
           env=env,
           stage_name=stage_names[0],
           **kwargs)

    # Build the rest stage by stage, using just built compiler to compile
    # the next stage.
    CmakeCommand.applyDefaultOptions(cmake_args, [
            # We should be warnings free when use just built compiler.
            ('-DLLVM_ENABLE_WERROR=', 'ON'),
            ])
    # If we build LLD, we would link with LLD.
    # Otherwise we link with a system linker.
    if 'lld' in f.depends_on_projects:
        CmakeCommand.applyDefaultOptions(cmake_args, [
            ('-DLLVM_ENABLE_LLD=', 'ON'),
            ])

    for stage_idx in range(1, stages):

        # Directories to use in this stage.
        obj_dir = f.stage_objdirs[stage_idx]
        src_dir = LLVMBuildFactory.pathRelativeToBuild(f.llvm_srcdir, obj_dir)
        install_dir = LLVMBuildFactory.pathRelativeToBuild(f.stage_installdirs[stage_idx], obj_dir)
        staged_install = f.stage_installdirs[stage_idx - 1]

        # Configure the compiler to use in this stage.
        cmake_args_stageN = cmake_args[:]
        CmakeCommand.applyRequiredOptions(cmake_args_stageN, [
            ('-DCMAKE_INSTALL_PREFIX=', install_dir),
            ])
        cmake_args_stageN.append(
            WithProperties(
                "-DCMAKE_CXX_COMPILER=%(workdir)s/" + staged_install + "/bin/clang++"
            ))
        cmake_args_stageN.append(
            WithProperties(
                "-DCMAKE_C_COMPILER=%(workdir)s/" + staged_install + "/bin/clang"
            ))

        addCmakeSteps(
           f,
           True, # We always do a clean build for the staged builds.
           obj_dir=stage_objdirs[stage_idx],
           install_dir=stage_installdirs[stage_idx],
           extra_configure_args=cmake_args_stageN,
           env=env,
           stage_name=stage_names[stage_idx],
           **kwargs)

        addNinjaSteps(
           f,
           obj_dir=stage_objdirs[stage_idx],
           env=env,
           stage_name=stage_names[stage_idx],
           **kwargs)

    return f
