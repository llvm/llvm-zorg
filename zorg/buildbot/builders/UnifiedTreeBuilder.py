# UnifiedTreeBuilder.py
#

from buildbot.plugins import steps, util
from buildbot.steps.shell import SetPropertyFromCommand
from buildbot.process.factory import BuildFactory

from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand
from zorg.buildbot.commands.LitTestCommand import LitTestCommand

from zorg.buildbot.conditions.FileConditions import FileDoesNotExist
from zorg.buildbot.process.factory import LLVMBuildFactory

import zorg.buildbot.builders.Util as builders_util

def getLLVMBuildFactoryAndPrepareForSourcecodeSteps(
           depends_on_projects = None,
           enable_runtimes = "auto",
           llvm_srcdir = None,
           src_to_build_dir = None,
           obj_dir = None,
           install_dir = None,
           cleanBuildRequested = None,
           env = None,
           **kwargs):

    def cleanBuildRequestedByProperty(step):
        return step.build.getProperty("clean")

    if cleanBuildRequested is None:
        # We want a clean checkout only if requested by the property.
        cleanBuildRequested = cleanBuildRequestedByProperty

    f = LLVMBuildFactory(
            depends_on_projects=depends_on_projects,
            enable_runtimes=enable_runtimes,
            llvm_srcdir=llvm_srcdir,
            src_to_build_dir=src_to_build_dir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            cleanBuildRequested=cleanBuildRequested,
            **kwargs) # Pass through all the extra arguments.

    # Remove the source code for a clean checkout if requested by property.
    # TODO: Some Windows workers do not handle RemoveDirectory command well.
    # So, consider running "rmdir /S /Q <dir>" if the build runs on Windows.
    f.addStep(steps.RemoveDirectory(name='clean-src-dir',
              dir=f.monorepo_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequestedByProperty,
              ))

    return f

def getLLVMBuildFactoryAndSourcecodeSteps(
           depends_on_projects = None,
           enable_runtimes = "auto",
           llvm_srcdir = None,
           src_to_build_dir = None,
           obj_dir = None,
           install_dir = None,
           cleanBuildRequested = None,
           **kwargs):

    f = getLLVMBuildFactoryAndPrepareForSourcecodeSteps(
            depends_on_projects=depends_on_projects,
            enable_runtimes=enable_runtimes,
            llvm_srcdir=llvm_srcdir,
            src_to_build_dir=src_to_build_dir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            cleanBuildRequested=cleanBuildRequested,
            **kwargs) # Pass through all the extra arguments.

    # Get the source code.
    f.addGetSourcecodeSteps(**kwargs)

    return f

def addCmakeSteps(
           f,
           cleanBuildRequested,
           obj_dir,
           generator=None,
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

    if obj_dir is None:
        obj_dir = f.obj_dir

    # This is an incremental build, unless otherwise has been requested.
    # Remove obj and install dirs for a clean build.
    # TODO: Some Windows workers do not handle RemoveDirectory command well.
    # So, consider running "rmdir /S /Q <dir>" if the build runs on Windows.
    f.addStep(steps.RemoveDirectory(name='clean-%s-dir' % obj_dir,
              dir=obj_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested,
              ))

    if f.enable_projects:
        CmakeCommand.applyDefaultOptions(cmake_args, [
            ('-DLLVM_ENABLE_PROJECTS=', ";".join(f.enable_projects)),
            ])

    if f.enable_runtimes:
        CmakeCommand.applyDefaultOptions(cmake_args, [
            ('-DLLVM_ENABLE_RUNTIMES=', ";".join(f.enable_runtimes)),
            ])

    if install_dir:
        install_dir_rel = LLVMBuildFactory.pathRelativeTo(
                              install_dir,
                              obj_dir)
        CmakeCommand.applyRequiredOptions(cmake_args, [
            ('-DCMAKE_INSTALL_PREFIX=', install_dir_rel),
            ])

        f.addStep(steps.RemoveDirectory(name='clean-%s-dir' % install_dir,
              dir=install_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested,
              ))

    # Reconcile the cmake options for this build.

    # Set proper defaults.
    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-DCMAKE_BUILD_TYPE=',        'Release'),
        ('-DLLVM_ENABLE_ASSERTIONS=',  'ON'),
        ('-DLLVM_LIT_ARGS=',           '-v -vv'),
        ])

    # Create configuration files with cmake, unless this has been already done
    # for an incremental build.
    if stage_name:
        step_name = "cmake-configure-%s" % stage_name
    else:
        stage_name = ""
        step_name = "cmake-configure"

    src_dir = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, obj_dir)

    # Make a local copy of the configure args, as we are going to modify that.
    definitions = dict()
    options = list()
    for d in  cmake_args:
        if isinstance(d, str) and d.startswith("-D"):
            k,v = d[2:].split('=', 1)
            definitions[k] = v
        else:
            options.append(d)

    f.addStep(CmakeCommand(name=step_name,
                          haltOnFailure=True,
                          description=["Cmake", "configure", stage_name],
                          generator=generator,
                          definitions=definitions,
                          options=options,
                          path=src_dir,
                          env=env or {},
                          workdir=obj_dir,
                          **kwargs # Pass through all the extra arguments.
                          ))

def addNinjaSteps(
           f,
           obj_dir = None,
           targets = None,
           checks = None,
           install_dir = None,
           env = None,
           stage_name = None,
           **kwargs):

    if obj_dir is None:
        obj_dir = f.obj_dir

    if stage_name:
        step_name = "{}-".format(stage_name)
        step_description=["Build", stage_name]
    else:
        stage_name = ""
        step_name = ""
        step_description=["Build"]

    if targets:
        step_name = "build-{}{}".format(step_name, "-".join(targets))
        step_description.extend(targets)
    else:
        step_name = "build-{}unified-tree".format(step_name)
        step_description.extend(["unified", "tree"])

    # Build the unified tree.
    f.addStep(NinjaCommand(name=step_name,
                           haltOnFailure=True,
                           targets=targets,
                           description=step_description,
                           env=env or {},
                           workdir=obj_dir,
                           **kwargs # Pass through all the extra arguments.
                           ))

    # Test just built components if requested.
    # Note: At this point env could be None, a dictionary, or a Property object.
    if isinstance(env, dict):
        check_env = env.copy() if env else dict()
        check_env['NINJA_STATUS'] = check_env.get('NINJA_STATUS', "%e [%u/%r/%f] ")
    else:
        check_env = env or {}

    for check in checks:
        f.addStep(LitTestCommand(name="test-%s-%s" % (step_name, check),
                                 command=['ninja', check],
                                 description=[
                                   "Test", "just", "built", "components", "for",
                                   check,
                                 ],
                                 env=check_env,
                                 workdir=obj_dir,
                                 **kwargs # Pass through all the extra arguments.
                                 ))

    # Install just built components
    if install_dir:
        # TODO: Run this step only if none of the prevous failed.
        f.addStep(NinjaCommand(name="install-%sall" % step_name,
                               targets=["install"],
                               description=["Install", "just", "built", "components"],
                               env=env or {},
                               workdir=obj_dir,
                               **kwargs # Pass through all the extra arguments.
                               ))

def getCmakeBuildFactory(
           depends_on_projects = None,
           enable_runtimes = "auto",
           llvm_srcdir = None,
           src_to_build_dir = None,
           obj_dir = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           install_pip_requirements = False,
           env = None,
           **kwargs):

    f = getLLVMBuildFactoryAndSourcecodeSteps(
            depends_on_projects=depends_on_projects,
            enable_runtimes=enable_runtimes,
            llvm_srcdir=llvm_srcdir,
            src_to_build_dir=src_to_build_dir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            **kwargs) # Pass through all the extra arguments.

    cleanBuildRequested = lambda step: step.build.getProperty("clean") or step.build.getProperty("clean_obj") or clean

    if install_pip_requirements:
        # Install python requirements, right now for MLIR
        # but can evolve to more projects later.
        f.addStep(steps.ShellCommand(
            name='install-mlir-requirements',
            command=["pip", "install", "-q", "-r", "../mlir/python/requirements.txt"],
            workdir=f.llvm_srcdir))

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
           enable_runtimes = "auto",
           targets = None,
           llvm_srcdir = None,
           src_to_build_dir = None,
           obj_dir = None,
           checks = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           install_pip_requirements = False,
           env = None,
           **kwargs):

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    if checks is None:
        checks = ['check-all']

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Be cautious and disable color output from all tools.
    }
    if env:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    # Some options are required for this build no matter what.
    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-G',                      'Ninja'),
        ])

    f = getCmakeBuildFactory(
            depends_on_projects=depends_on_projects,
            enable_runtimes=enable_runtimes,
            llvm_srcdir=llvm_srcdir,
            src_to_build_dir=src_to_build_dir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            clean=clean,
            extra_configure_args=cmake_args,
            install_pip_requirements=install_pip_requirements,
            env=merged_env,
            **kwargs) # Pass through all the extra arguments.

    addNinjaSteps(
           f,
           obj_dir=f.obj_dir,
           targets=targets,
           checks=checks,
           install_dir=f.install_dir,
           env=merged_env,
           **kwargs)

    return f

def getCmakeWithNinjaWithMSVCBuildFactory(
           depends_on_projects = None,
           enable_runtimes = "auto",
           targets = None,
           llvm_srcdir = None,
           src_to_build_dir = None,
           obj_dir = None,
           checks = None,
           install_dir = None,
           clean = False,
           extra_configure_args = None,
           # VS tools environment variable if using MSVC. For example,
           # %VS140COMNTOOLS% selects the 2015 toolchain.
           vs=None,
           target_arch=None,
           install_pip_requirements = False,
           env = None,
           **kwargs):

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    if checks is None:
        checks = ['check-all']

    f = getLLVMBuildFactoryAndSourcecodeSteps(
            depends_on_projects=depends_on_projects,
            enable_runtimes=enable_runtimes,
            llvm_srcdir=llvm_srcdir,
            src_to_build_dir=src_to_build_dir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            **kwargs) # Pass through all the extra arguments.

    f.addStep(SetPropertyFromCommand(
        command=builders_util.getVisualStudioEnvironment(vs, target_arch),
        extract_fn=builders_util.extractVSEnvironment,
        env=env or {}))
    env = util.Property('vs_env')

    cleanBuildRequested = lambda step: step.build.getProperty("clean") or step.build.getProperty("clean_obj") or clean

    if install_pip_requirements:
        # Install python requirements, right now for MLIR
        # but can evolve to more projects later.
        f.addStep(steps.ShellCommand(
            name='install-mlir-requirements',
            command=["pip", "install", "-q", "-r", "../mlir/python/requirements.txt"],
            workdir=f.llvm_srcdir))

    addCmakeSteps(
        f,
        generator='Ninja',
        cleanBuildRequested=cleanBuildRequested,
        obj_dir=f.obj_dir,
        install_dir=f.install_dir,
        extra_configure_args=cmake_args,
        env=env,
        **kwargs)

    addNinjaSteps(
           f,
           targets=targets,
           obj_dir=obj_dir,
           checks=checks,
           install_dir=f.install_dir,
           env=env,
           **kwargs)

    return f

def getCmakeWithNinjaMultistageBuildFactory(
           depends_on_projects = None,
           enable_runtimes = "auto",
           llvm_srcdir = None,
           src_to_build_dir = None,
           obj_dir = None,
           checks = None,
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

    if checks is None:
        checks = ['check-all']

    stage_objdirs = list()
    stage_installdirs = list()
    for s in stage_names:
        stage_objdirs.append("%s/%s" % (obj_dir, s))
        stage_installdirs.append("%s/%s" % (install_dir, s))

    f = getLLVMBuildFactoryAndPrepareForSourcecodeSteps(
            depends_on_projects=depends_on_projects,
            enable_runtimes=enable_runtimes,
            llvm_srcdir=llvm_srcdir,
            src_to_build_dir=src_to_build_dir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            env=merged_env,
            stage_objdirs=stage_objdirs,
            stage_installdirs=stage_installdirs,
            stage_names=stage_names,
            **kwargs) # Pass through all the extra arguments.

    # Get the source code.
    # We have consumed kwargs specific to this factory, so
    # it is safe to pass all the remaining kwargs down.
    f.addGetSourcecodeSteps(**kwargs)

    # Set proper defaults.
    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-DCMAKE_BUILD_TYPE=',        'Release'),
        ('-DLLVM_BUILD_TESTS=',        'ON'),
        ('-DLLVM_ENABLE_ASSERTIONS=',  'OFF'),
        ('-DLLVM_OPTIMIZED_TABLEGEN=', 'ON'),
        ])

    if 'clang' in depends_on_projects:
        CmakeCommand.applyDefaultOptions(cmake_args, [
            ('-DCLANG_BUILD_EXAMPLES=',    'OFF'),
            ])

    # The stage 1 is special, though. We use the system compiler and
    # do incremental build, unless a clean one has been requested.
    cmake_args_stage1 = cmake_args[:]
    CmakeCommand.applyDefaultOptions(cmake_args_stage1, [
        # Do not expect warning free build by the system toolchain.
        ('-DLLVM_ENABLE_WERROR=',      'OFF'),
        ])

    cleanBuildRequested = lambda step: step.build.getProperty("clean") or step.build.getProperty("clean_obj") or clean

    addCmakeSteps(
           f,
           generator='Ninja',
           cleanBuildRequested=cleanBuildRequested,
           obj_dir=stage_objdirs[0],
           install_dir=stage_installdirs[0],
           extra_configure_args=cmake_args_stage1,
           env=merged_env,
           stage_name=stage_names[0],
           **kwargs)

    addNinjaSteps(
           f,
           obj_dir=stage_objdirs[0],
           checks=checks,
           install_dir=stage_installdirs[0],
           env=merged_env,
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
        src_dir = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, obj_dir)
        install_dir = LLVMBuildFactory.pathRelativeTo(f.stage_installdirs[stage_idx], obj_dir)
        staged_install = f.stage_installdirs[stage_idx - 1]

        # Configure the compiler to use in this stage.
        cmake_args_stageN = cmake_args[:]
        CmakeCommand.applyRequiredOptions(cmake_args_stageN, [
            ('-DCMAKE_INSTALL_PREFIX=', install_dir),
            ])
        cmake_args_stageN.append(
            util.Interpolate(
                f"-DCMAKE_CXX_COMPILER=%(prop:builddir)s/{staged_install}/bin/clang++"
            ))
        cmake_args_stageN.append(
            util.Interpolate(
                f"-DCMAKE_C_COMPILER=%(prop:builddir)s/{staged_install}/bin/clang"
            ))

        addCmakeSteps(
           f,
           generator='Ninja',
           cleanBuildRequested=True, # We always do a clean build for the staged builds.
           obj_dir=stage_objdirs[stage_idx],
           install_dir=stage_installdirs[stage_idx],
           extra_configure_args=cmake_args_stageN,
           env=merged_env,
           stage_name=stage_names[stage_idx],
           **kwargs)

        addNinjaSteps(
           f,
           obj_dir=stage_objdirs[stage_idx],
           checks=checks,
           install_dir=stage_installdirs[stage_idx],
           env=merged_env,
           stage_name=stage_names[stage_idx],
           **kwargs)

    return f


def getCmakeExBuildFactory(
        depends_on_projects = None,
        enable_runtimes = "auto",
        cmake_definitions = None,
        cmake_options = None,
        allow_cmake_defaults = True,    # Add default CMake definitions to build LLVM project (if not specified).
        targets = ".",
        install_targets = "install",
        checks = "check-all",
        checks_on_target = None,
        generator = "Ninja",            # CMake generator.
        vs = None,                      # VS tools environment variable if using MSVC.
        vs_arch = None,
        clean = False,                  # Do clean build flag.
        repo_profiles = "default",      # The source code repository profiles.
        extra_git_args = None,          # Extra parameters for steps.Git step (such as 'config', 'workdir', etc.)
        llvm_srcdir = None,             # A custom LLVM src directory within %(prop:builddir)s of the builder.
        src_to_build_dir = None,
        obj_dir = None,
        install_dir = None,
        pre_configure_steps = None,
        post_build_steps = None,
        pre_install_steps = None,
        post_finalize_steps = None,
        jobs = None,                    # Restrict a degree of parallelism.
        env  = None,                    # Common environmental variables.
        hint = None,
    ):

    """ Create and configure a builder factory to build a LLVM project from the unified source tree.

        This is one-stage CMake configurable build that uses Ninja generator by default. Using the other CMake generators
        also possible.

        Property Parameters
        -------------------

        clean : boolean
            Clean up the source and the build folders.

        clean_obj : boolean
            Clean up the build folders.


        Parameters
        ----------

        depends_on_projects : list, optional
            A list of LLVM projects this builder depends on (default is None).

            These project names will be used to set up the proper schedulers. Also these names will be used
            to prepare the factory's 'enable_projects' and 'enable_runtimes' lists.

            If this parameter is not None and contains the non-runtime project names, they will go to
            LLVM_ENABLE_PROJECTS CMake configuration parameter.

        enable_runtimes : list, optional
            A list of the runtime project names for the build (default is 'auto'). This list goes into
            the factory's 'enable_runtimes' attribute and LLVM_ENABLE_RUNTIMES CMake configuration parameter.

            If "auto" is specified, the runtime projects will be extracted from 'depends_on_projects' parameter.

            If None is specified, LLVM_ENABLE_RUNTIMES will not be set for the CMake configuration step.

            (see LLVMBuildFactory for more details).

        cmake_definitions : dict, optional
            A dictionary of the CMake definitions (default is None).

        cmake_options : list, optional
            A list of the CMake options (default is None).

        allow_cmake_defaults : boolean
            Add default CMake definitions to the build configuration step (default True).

            A default value will be used only if a definition is not explicitly specified in 'cmake_definitions'
            argument and allow_cmake_defaults evaluates to True.

        targets : list, optional
            A list of targets to build (default is ["."]).
            Each target gets built in a separate step, skipped if None.

            Pass string '.' in a list to build the default target.

        install_targets : list, optional
            A list of the installation targets (default is ["install"]).

            Each target gets installed in a separate step.

            NOTE: 'install_dir' argument must be specified if there are install_targets.

        checks : list, optional
            A list of the check targets (default is ["check-all"]).

            Each check target gets executed in a separate step. The check step uses LitTestCommand
            to parse and display the test result logs.

            No check steps will be generated for the build if 'None' was provided with this argument.

        checks_on_target : list of tuples, optional
            A list of commands to run the tests on the remote dev boards (default is None).

            This argument expects a list of tuples with test names to display and the test commands to execute.
            For example:
            ```
            checks_on_target=[
                ("libunwind",
                    ["python", "bin/llvm-lit.py", "-v", "--time-tests", "--threads=32",
                     "runtimes/runtimes-armv7-unknown-linux-gnueabihf-bins/libunwind/test"]
                ),
                ...
            ]
            ```

        generator : str, required
            CMake generator (default is 'Ninja').

            See CMake documentation for more details.

        vs : str, optional
            Set up Visual Studio environment for the build (default is None).

            Possible values are "autodetect", "manual" or None.

        vs_arch : str, optional
            Provide a build host arch for the Visual Studio tools (default is None)

            Possible values are None, "amd64", "x64", etc. Please see Visual Studio documentation for more details.

        clean : boolean
            Alsways do a clean build (default is False).

        repo_profiles : string, optional
            A name of the source code profile to get from the remote repository. Currently is supported only "default"
            profile and None. Default is "default".

            If None is passed, no the repository checkout steps will be added to the factory workflow. This is useful
            for the nested factories when the single repo is shared between them.

        extra_git_args : dict, optional
            Provide extra arguments for the Git step (default is None).

            Sometimes it is necessary to pass some additional parameters to the git step, such as
            'config', 'workdir', etc.

        llvm_srcdir : str, optional
            A custom LLVM src directory within %(prop:builddir)s of the builder (default is "llvm-project").

            (see LLVMBuildFactory for more details).

        src_to_build_dir : str, optional
            A specific root project directory within the LLVM source code to configure and build (default is "llvm").

            Provide a relative path to sub-project within the llvm-project directory to start configuring with instead of
            default llvm folder.

            For example: pass "flang/runtime" to configure and build the Flang runtime sub-project.

            (see LLVMBuildFactory for more details).

        obj_dir : str, optional
            The build folder (default is "build").

            (see LLVMBuildFactory for more details).

        install_dir : str, optional
            The installation folder (default is None).

            Provide the installation folder and the install targets to add the installation steps to the final build.

        pre_configure_steps : list or LLVMFactory, optional
            The buildflow customization steps to execute before the CMake configuration step.

            Provide a list of build step objects or LLVMFactory object.

        post_build_steps : list or LLVMFactory, optional
            The buildflow customization steps to execute after the build step, but before the check steps.

            Provide a list of build step objects or LLVMFactory object.

        pre_install_steps : list or LLVMFactory, optional
            The buildflow customization steps to execute after the check steps, but before the installation steps (if requested).

            Provide a list of build step objects or LLVMFactory object.

        post_finalize_steps : list or LLVMFactory, optional
            The buildflow customization steps to execute at the end of the build workflow.

            Provide a list of build step objects or LLVMFactory object.

        jobs : int, optional
            Restrict a degree of parallelism (default is None).

        env : dict, optional
            Common environmental variables for all build steps (default is None).

        hint : string, optional
            Use this hint to apply suffixes to the step names when factory is used as a nested factory for another one.
            The suffix will be added to the step name separated by dash symbol.

            As example, passing of 'stageX' with 'hint' will force generating of the following step names:
                cmake-cofigure => cmake-configure-stageX
                build => build-stageX
                install => install-stageX
                & etc.

        Returns
        -------

        Returns the factory object with prepared build steps.

        Properties
        ----------

        The factory sets some properties to provide more flexible configuration for the builders:

        srcdir
            Relative path to the source code root directory ("llvm-project" by default).

            "%(prop:builddir)s/%(prop:srcdir)s" is a fully qualified path to the source code dir.

        srcdir_relative
            Path to the source code root directory relative to the objdir ("../llvm-project" by default).

        objdir
            Relative path to the build directory.

            "%(prop:builddir)s/%(prop:objdir)s" is a fully qualified path to the obj dir.

        depends_on_projects
            A list of LLVM projects this builder depends on. It will build commits to these projects.

        enable_projects
            A list of enabled projects.

        enable_runtimes
            A list of enabled runtimes.

    """
    assert generator, "CMake generator must be specified."
    assert not pre_configure_steps or isinstance(pre_configure_steps, (list, BuildFactory)), \
                                                 "The 'pre_configure_steps' argument must be a list() or BuildFactory()."
    assert not post_build_steps or isinstance(post_build_steps, (list, BuildFactory)), \
                                                 "The 'post_build_steps' argument must be a list() or BuildFactory()."
    assert not pre_install_steps or isinstance(pre_install_steps, (list, BuildFactory)), \
                                                 "The 'pre_install_steps' argument must be a list() or BuildFactory()."
    assert not post_finalize_steps or isinstance(post_finalize_steps, (list, BuildFactory)), \
                                                 "The 'post_finalize_steps' argument must be a list() or BuildFactory()."

    # This function extends the current workflow with provided custom steps.
    def extend_with_custom_steps(fc, s):
        # We already got either list() or LLVMBuildFactory() object here.
        fc.addSteps(s.steps if isinstance(s, BuildFactory) else s)

    def norm_target_list_arg(lst):
        if type(lst) == str:
            lst = list(filter(None, lst.split(";")))
        # In case we got IRenderable, just wrap it into the list.
        if not isinstance(lst, list):
            lst = [ lst ]
        return lst

    # Normalize all arguments with a list of the targets.
    # We need to convert them into the regular lists of str/IRenderable objects or empty list.
    targets = norm_target_list_arg(targets or [])
    install_targets = norm_target_list_arg(install_targets or [])
    checks = norm_target_list_arg(checks or [])
    checks_on_target = checks_on_target or []

    env = env or {}
    # Do not everride TERM just in case.
    if not "TERM" in env:
        # Be cautious and disable color output from all tools.
        env.update({ 'TERM' : 'dumb' })

    if not "NINJA_STATUS" in env and generator.upper() == "NINJA":
        env.update({ 'NINJA_STATUS' : "%e [%u/%r/%f] " })

    # Default root factory. We will collect all steps for all stages here.
    f = LLVMBuildFactory(
            depends_on_projects = depends_on_projects,
            enable_runtimes     = enable_runtimes,
            hint                = hint,
            llvm_srcdir         = llvm_srcdir,
            src_to_build_dir    = src_to_build_dir,
            obj_dir             = obj_dir,
            install_dir         = install_dir,
        )

    f.addSteps([
        # Set up some properties, which could be used to configure the builders.
        steps.SetProperties(
            name            = f.makeStepName('set-props'),
            properties      = {
                "depends_on_projects"   : ";".join(sorted(f.depends_on_projects)),
                "enable_projects"       : ";".join(sorted(f.enable_projects)),
                "enable_runtimes"       : ";".join(sorted(f.enable_runtimes)),
                "srcdir"                : f.monorepo_dir,
                "srcdir_relative"       : LLVMBuildFactory.pathRelativeTo(f.monorepo_dir, f.obj_dir),
                "objdir"                : f.obj_dir,
            }
        ),

        # This is an incremental build, unless otherwise has been requested.
        # Remove obj dirs for a clean build.
        steps.RemoveDirectory(
            name            = f.makeStepName('clean-obj-dir'),
            dir             = f.obj_dir,
            description     = ["Remove", f.obj_dir, "directory"],
            haltOnFailure   = False,
            flunkOnFailure  = False,
            doStepIf        = lambda step, clean = clean: clean or step.getProperty("clean_obj") == True
        ),
    ])

    # Let's start from getting the source code. We share it between all stages.

    # Add the Git step.
    if repo_profiles == "default":
        f.addSteps([
            # Remove the source code for a clean checkout if requested by property.
            steps.RemoveDirectory(
                name            = f.makeStepName('clean-src-dir'),
                dir             = f.monorepo_dir,
                description     = ["Remove", f.monorepo_dir, "directory"],
                haltOnFailure   = False,
                flunkOnFailure  = False,
                doStepIf        = util.Property("clean", False) == True,
            ),
        ])

        extra_git_args = extra_git_args or {}

        f.addGetSourcecodeSteps(**extra_git_args)

    # Add custom pre-configuration steps if specified.
    if pre_configure_steps:
        extend_with_custom_steps(f, pre_configure_steps)

    # Configure MSVC environment if requested.
    if vs:
        f.addStep(
            steps.SetPropertyFromCommand(
                name            = f.makeStepName("set-props.vs_env"),
                command         = builders_util.getVisualStudioEnvironment(vs, vs_arch),
                extract_fn      = builders_util.extractVSEnvironment,
                env             = env
            ))
        env = util.Property('vs_env')

    # Build the CMake command definitions.
    cmake_definitions = cmake_definitions or dict()
    assert isinstance(cmake_definitions, dict), "The CMake definitions argument must be a dictionary."
    cmake_options = cmake_options or list()
    assert isinstance(cmake_options, list), "The CMake options argument must be a list."

    if not "LLVM_ENABLE_PROJECTS" in cmake_definitions and f.enable_projects:
        cmake_definitions.update({ "LLVM_ENABLE_PROJECTS" : ";".join(sorted(f.enable_projects)) })

    if not "LLVM_ENABLE_RUNTIMES" in cmake_definitions and f.enable_runtimes:
        cmake_definitions.update({ "LLVM_ENABLE_RUNTIMES" : ";".join(sorted(f.enable_runtimes)) })

    if not "CMAKE_INSTALL_PREFIX" in cmake_definitions and f.install_dir:
        cmake_definitions.update({ "CMAKE_INSTALL_PREFIX" : LLVMBuildFactory.pathRelativeTo(
                                                                f.install_dir,
                                                                f.obj_dir) })
        # Remove install directory.
        f.addSteps([
            steps.RemoveDirectory(
                name            = f.makeStepName("clean-install-dir"),
                dir             = install_dir, #TODO:f.install_dir,
                description     = ["Remove", f.install_dir, "directory"],
                haltOnFailure   = False,
                flunkOnFailure  = False,
                doStepIf        = lambda step, clean = clean: clean or step.getProperty("clean_obj") == True
            ),
        ])

    # Set proper defaults.
    if allow_cmake_defaults:
        if not "CMAKE_BUILD_TYPE" in cmake_definitions:
            cmake_definitions.update({ "CMAKE_BUILD_TYPE" : "Release" })
        if not "LLVM_ENABLE_ASSERTIONS" in cmake_definitions:
            cmake_definitions.update({ "LLVM_ENABLE_ASSERTIONS" : "ON" })
        if not "LLVM_LIT_ARGS" in cmake_definitions and checks:
            cmake_definitions.update({ "LLVM_LIT_ARGS" : "-v --time-tests" })

    f.addStep(
        steps.CMake(
            name            = f.makeStepName("cmake-configure"),
            path            = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, f.obj_dir),
            generator       = generator,
            definitions     = cmake_definitions,
            options         = cmake_options,
            description     = ["CMake configure"],
            haltOnFailure   = True,
            env             = env,
            workdir         = f.obj_dir
        ))

    hint_suffix = f"-{hint}" if hint else None
    # Build Commands.
    #NOTE: please note that the default target (.) cannot be specified by the IRenderable object.
    for target in targets:
        cmake_build_options = ["--build", "."]
        if target != ".":
            cmake_build_options.extend(["--target", target])
        if jobs:
            cmake_build_options.extend(["--", "-j", jobs])

        target_title = "default" if target == "." else target

        f.addStep(
            steps.CMake(
                name            = util.Interpolate("build-%(kw:title)s%(kw:hint:-)s",
                                                   title = target_title, hint = hint_suffix),
                options         = cmake_build_options,
                description     = ["Build target", target_title],
                haltOnFailure   = True,
                env             = env,
                workdir         = f.obj_dir
            ))

    # Add the custom post-build workflow extension steps, if specified.
    if post_build_steps:
        extend_with_custom_steps(f, post_build_steps)

    # Check Commands.
    for target in checks:
        f.addStep(
            LitTestCommand(
                name            = util.Interpolate("test-%(kw:title)s%(kw:hint:-)s",
                                                   title = target, hint = hint_suffix),
                command         = [steps.CMake.DEFAULT_CMAKE, "--build", ".", "--target", target],
                description     = ["Test just built components:", target],
                descriptionDone = ["Test just built components:", target, "completed"],
                haltOnFailure   = False, # We want to test as much as we could.
                env             = env,
                workdir         = f.obj_dir
            ))

    # Target Check Commands.
    for target, cmd in checks_on_target:
        f.addStep(
            LitTestCommand(
                name            = util.Interpolate("test-%(kw:title)s%(kw:hint:-)s",
                                                   title = target, hint = hint_suffix),
                command         = cmd,
                description     = ["Test just built components:", target],
                descriptionDone = ["Test just built components:", target, "completed"],
                haltOnFailure   = False, # We want to test as much as we could.
                env             = env,
                workdir         = f.obj_dir
            ))

    # Add the custom pre-installation workflow extension steps, if specified.
    if pre_install_steps:
        extend_with_custom_steps(f, pre_install_steps)

    # Process the installation targets.
    if f.install_dir and install_targets:
        for target in install_targets:
            f.addStep(
                steps.CMake(
                    name            = util.Transform(lambda s: s if s.startswith("install") else f"install-{s}",
                                                     util.Interpolate("%(kw:title)s%(kw:hint:-)s", title = target, hint = hint_suffix)),
                    options         = ["--build", ".", "--target", target],
                    description     = ["Install just built components:", target],
                    haltOnFailure   = False,
                    env             = env,
                    workdir         = f.obj_dir
                ))

    # Add the custom finalize workflow extension steps, if specified.
    if post_finalize_steps:
        extend_with_custom_steps(f, post_finalize_steps)

    return f
