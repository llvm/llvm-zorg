# StagedBuilder.py
#
# The factory provides a staged builder configuration to build the LLVM project unified tree.

from buildbot.plugins import steps, util

from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.process.factory import LLVMBuildFactory, _all_runtimes as LLVMRuntimes

import zorg.buildbot.builders.Util as builders_util

def getCmakeBuildFactory(
        llvm_srcdir = None,         # A custom LLVM src directory within %(prop:builddir)s of the builder.
        generator = "Ninja",        # CMake generator.
        clean = False,              # Do clean build flag.
        stages = None,              # A list of dict() or LLVMBuildFactory() objects that represent the build stages.
        extra_git_args = None,      # Extra parameters for steps.Git step (such as 'config', 'workdir' & etc.)
        jobs = None,                # Restrict a degree of parallelism.
        env  = None,                # Environmental variables for all stages.
    ):
    """ Create and configure a simple multi-staged builder factory to build the LLVM projects from the unified source tree.

        This is CMake configurable build that uses Ninja generator by default. Using the other CMake generators
        also possible.

        Every builder stage includes a pair of cmake configuration and build steps by default.
        The optional steps are the checks (local and remote/custom) and the installation steps.

        Also the builder factory accepts the LLVMBuildFactory object prepared by any other build factories
        as own build stage.


        Property Parameters
        -------------------

        clean : boolean
            Clean up the source and the build folders.

        clean_obj : boolean
            Clean up the build folders.


        Parameters
        ----------

        llvm_srcdir : str, optional
            A custom LLVM src directory within %(prop:builddir)s of the builder (default is "llvm-project").

            (see LLVMBuildFactory for more details).

        generator : str, required
            The CMake generator (default is 'Ninja').

            See CMake documentation for more details.

        clean : boolean
            Alsways do a clean build (default is False).

        stages : list, required
            A list of dict() or LLVMBuildFactory() objects with the stage descriptions.

            Each object represents a single CMake configurable (dict()) or custom (LLVMBuildFactory()) build configuration.

            See [Stage Parameters] section for more details.

        extra_git_args : dict, optional
            Provide extra arguments for the Git step (default is None).

            Sometimes is necessary to pass some additional parameters into the git step, such as
            'config', 'workdir' & etc.

        jobs : int, optional
            Restrict a degree of parallelism (default is None).

        env : dict, optional
            Common environmental variables for all stages (default is None).


        Stage Parameters
        ----------------

        The parameters for the stage object, passed to the factory.

        NOTE: All stages get their own 'obj' directories in format %(prop:builddir)s/build/<stage_name>. It cannot be changed.


        depends_on_projects : list, optional
            A list of the depended projects (default is None).

            These project names will be used to set up the proper schedulers. Also these names will be used
            to prepare the factory's 'enable_projects' and 'enable_runtimes' lists.

            If this parameter is not None and contains the non-runtime project names, they will go to
            LLVM_ENABLE_PROJECTS CMake configuration parameter.

        enable_runtimes : list, optional
            A list of the runtime project names for the build (default is 'auto'). This list goes into
            the factory's 'enable_runtimes' attribute and LLVM_ENABLE_RUNTIMES CMake configuration parameter.

            If "auto" is specified, the runtime projects will be extracted from 'depends_on_projects' parameter.

            If None is specified, LLVM_ENABLE_RUNTIMES will avoided for the CMake configuration step.

            (see LLVMBuildFactory for more details).

        cmake_definitions : dict, optional
            A dictionary of the CMake definitions (default is None).

        cmake_options : list, optional
            A list of the CMake options (default is None).

        targets : list, optional
            A list of targets to build (default is ["."]).

            Pass '.' in a list to build the default target. Each target gets built with own step.

            No build steps will be generated for the build if 'None' was provided with this argument.

        install_targets : list, optional
            A list of the installation targets (default is ["install"]).

            Each target gets installed with own step.

            NOTE: the 'install_dir' argument also must be provided to add the installation steps.

        checks : list, optional
            A list of the check targets (default is ["check-all"]).

            Each check target gets executed with own step. The check step uses LitTestCommand
            to parse and display the test result logs.

            No check steps will be generated for the build if 'None' was provided with this argument.

        checks_on_target : list of tuples, optional
            A list of commands to run the tests on the remote dev boards (default is None).

            This argument expects a list of tuples, where is a name of the test (to display) and
            the test command to execute:
            ```
            checks_on_target=[
                ("libunwind",
                    ["python", "bin/llvm-lit.py", "-v", "-vv", "--threads=32",
                     "runtimes/runtimes-armv7-unknown-linux-gnueabihf-bins/libunwind/test"]
                ),
                ...
            ]
            ```

        vs : str, optional
            Set up Visual Studio environment for the build (default is None).

            Possible values are "autodetect", "manual" or None.

        vs_arch : str, optional
            Provide a build host arch for the Visual Studio tools (default is None)

            Possible values are None, "amd64", "x64" & etc.

        src_to_build_dir : str, optional
            A specific root project directory within the LLVM source code to configure and build (default is "llvm").

            Provide a relative path to sub-project within the llvm-project directory to start configuring with instead of
            default llvm folder.

            As example: pass "flang/runtime" to configure and build the Flang runtime sub-project.

            (see LLVMBuildFactory for more details).

        install_dir : str, optional
            The installation folder (default is None).

            Provide the installation folder and the install targets to add the installation steps to the final build.

        env : dict, optional
            The stage specific environmental variables (default is None).



        Returns
        -------

        Returns the factory object with prepared build steps.

        Properties
        ----------

        The factory sets some properties to provide more flexible configuration for the builders:

        srcdir
            Relative path to the source code root directory ("llvm-project" by default).

            "%(prop:builddir)s/%(prop:srcdir)s" is a full path to the source code dir.

        srcdir_relative
            Relative path from the obj dir to the source code root dir ("../llvm-project" by default).

        objrootdir
            Relative path to the build directory.

            "%(prop:builddir)s/%(prop:objrootdir)s/<stage-name>" is a full path to the stage's obj dir.

        depends_on_projects
            A list of the depended projects for the build.

        enable_projects
            A list of enabled projects for all stages.

        enable_runtimes
            A list of enabled runtimes for all stages.

    """
    assert generator, "The CMake generator must be specified."
    assert stages, "At least one stage must be specified."
    assert isinstance(stages, list), "The 'stages' argument must be a list of dict() or LLVMBuildFactory()."

    obj_root_dir = "build"

    env = env or {}
    # Do not everride TERM just in case.
    if not "TERM" in env:
        # Be cautious and disable color output from all tools.
        env.update({ 'TERM' : 'dumb' })

    if not "NINJA_STATUS" in env and generator.upper() == "NINJA":
        env.update({ 'NINJA_STATUS' : "%e [%u/%r/%f] " })

    # Default root factory. We will collect all steps for all stages here.
    f = LLVMBuildFactory(
            llvm_srcdir     = llvm_srcdir,
            obj_dir         = obj_root_dir
        )

    f.addSteps([
        # Remove the source code for a clean checkout if requested by property.
        steps.RemoveDirectory(
            name            = 'clean-src-dir',
            dir             = f.monorepo_dir,
            haltOnFailure   = False,
            flunkOnFailure  = False,
            doStepIf        = util.Property("clean", False) == True,
        ),

        # This is an incremental build, unless otherwise has been requested.
        # Remove obj dirs for a clean build.
        steps.RemoveDirectory(
            name            = 'clean-obj-dir',
            dir             = util.Interpolate(obj_root_dir),
            haltOnFailure   = False,
            flunkOnFailure  = False,
            doStepIf        = lambda step, clean = clean: clean or step.getProperty("clean_obj") == True
        ),
    ])

    # Get the source code steps at first. We share it between all stages.

    # Add the Git step.
    extra_git_args = extra_git_args or {}

    f.addGetSourcecodeSteps(**extra_git_args)

    # Walk over all stages.
    stage_factories = []

    # Set up consolidated projects/runtimes/dependencies for the result factory.
    def normalize_factory(result_factory, stage_factory):
        # Add extra depended projects to trigger the schedulers.
        if stage_factory.depends_on_projects:
            result_factory.depends_on_projects = set(result_factory.depends_on_projects.union(stage_factory.depends_on_projects))
        if stage_factory.enable_runtimes:
            result_factory.enable_runtimes = frozenset(result_factory.enable_runtimes.union(stage_factory.enable_runtimes))
            result_factory.depends_on_projects = set(result_factory.depends_on_projects.union(stage_factory.enable_runtimes))
        # Update a list of enabled projects for the result factory.
        # LLVMRuntimes => factory._all_runtimes
        result_factory.enable_projects = result_factory.depends_on_projects.difference(LLVMRuntimes)

    for stage in stages:
        # If we got already prepared factory as a build stage, just store it for later processing.
        if isinstance(stage, LLVMBuildFactory):
            normalize_factory(f, stage)
            stage_factories.append(stage)
            continue

        assert isinstance(stage, dict), "The stage object must be dict() or LLVMBuildFactory() " \
                                        "in StagedBuilder.getCmakeBuildFactory(stages) argument."

        stage_name = stage.get("name")
        assert stage_name, "A stage name must be specified."

        stage_obj_dir = f"{obj_root_dir}/{stage_name}"

        depends_on_projects     = stage.get("depends_on_projects")      # None or a list of the projects.
        enable_runtimes         = stage.get("enable_runtimes")          # None, "auto" or a list of the projects.
        cmake_definitions       = stage.get("cmake_definitions", {})
        cmake_options           = stage.get("cmake_options", [])
        targets                 = stage.get("targets", ["."])           # None (default target) or a list of the targets.
        checks                  = stage.get("checks", [])               # None (no check) or a list of the check targets.
        checks_on_target        = stage.get("checks_on_target", [])     # None (no target checks) or a list of the target check commands.
        src_to_build_dir        = stage.get("src_to_build_dir")         # None (default: llvm) or a path the project's root inside of the llvm-project directory.
        install_dir             = stage.get("install_dir")
        install_targets         = stage.get("install_targets", ["install"])
        stage_env               = stage.get("env", {})
        # VS tools environment variable if using MSVC.
        vs                      = stage.get("vs")                       # None, "autodetect", "manual"
        vs_arch                 = stage.get("vs_arch")                  # None, "amd64", "x64" & etc.

        # The stage factory. This factory will be merged into the root factory.
        stage_f = LLVMBuildFactory(
                depends_on_projects = depends_on_projects,
                enable_runtimes     = enable_runtimes,
                llvm_srcdir         = llvm_srcdir,
                src_to_build_dir    = src_to_build_dir,
                obj_dir             = stage_obj_dir,
                install_dir         = install_dir
            )

        stage_env.update(env)

        # Configure MSVC environment at first if requested.
        if vs:
            stage_f.addStep(
                steps.SetPropertyFromCommand(
                    name            = "set-pros.vs_env",
                    command         = builders_util.getVisualStudioEnvironment(vs, vs_arch),
                    extract_fn      = builders_util.extractVSEnvironment,
                    env             = stage_env
                ))
            stage_env = util.Property('vs_env')

        # CMake command.
        if not "LLVM_ENABLE_PROJECTS" in cmake_definitions and stage_f.enable_projects:
            cmake_definitions.update({ "LLVM_ENABLE_PROJECTS" : ";".join(stage_f.enable_projects) })

        if not "LLVM_ENABLE_RUNTIMES" in cmake_definitions and stage_f.enable_runtimes:
            cmake_definitions.update({ "LLVM_ENABLE_RUNTIMES" : ";".join(stage_f.enable_runtimes) })

        if not "CMAKE_INSTALL_PREFIX" in cmake_definitions and stage_f.install_dir:
            cmake_definitions.update({ "CMAKE_INSTALL_PREFIX" : LLVMBuildFactory.pathRelativeTo(
                                                                    stage_f.install_dir,
                                                                    stage_f.obj_dir) })
            # Remove all install directories for the stage.
            stage_f.addSteps([
                steps.RemoveDirectory(
                    name            = f"clean-install-dir-{stage_name:.30}",
                    dir             = util.Interpolate(stage_f.install_dir),
                    haltOnFailure   = False,
                    flunkOnFailure  = False,
                    doStepIf        = lambda step, clean = clean: clean or step.getProperty("clean_obj") == True
                ),
            ])

        stage_f.addStep(
            steps.CMake(
                name            = f"cmake-configure-{stage_name:.32}",
                path            = LLVMBuildFactory.pathRelativeTo(stage_f.llvm_srcdir, stage_f.obj_dir),
                generator       = generator,
                definitions     = cmake_definitions,
                options         = cmake_options,
                description     = ["CMake configure", stage_name],
                haltOnFailure   = True,
                env             = stage_env,
                workdir         = stage_f.obj_dir
            ))

        # Build Commands.
        for target in (targets or []):
            cmake_build_options = ["--build", "."]
            if target != ".":
                cmake_build_options.extend(["--target", target])
            if jobs:
                cmake_build_options.extend(["--", "-j", jobs])

            target_title = "default" if target == "." else target

            stage_f.addStep(
                steps.CMake(
                    name            = f"build-{stage_name}-{target_title}"[:48],
                    options         = cmake_build_options,
                    description     = ["Build", stage_name, "target", target_title],
                    haltOnFailure   = True,
                    env             = stage_env,
                    workdir         = stage_f.obj_dir
                ))

        # Check Commands.
        for target in (checks or []):
            stage_f.addStep(
                LitTestCommand(
                    name            = f"test-{stage_name}-{target}"[:48],
                    command         = [steps.CMake.DEFAULT_CMAKE, "--build", ".", "--target", target],
                    description     = ["Test just built components for", stage_name, ":", target],
                    descriptionDone = ["Test just built components for", stage_name, ":", target, "completed"],
                    haltOnFailure   = False, # We want to test as much as we could.
                    env             = stage_env,
                    workdir         = stage_f.obj_dir
                ))

        # Target Check Commands.
        for check, cmd in checks_on_target:
            stage_f.addStep(
                LitTestCommand(
                    name            = f"test-{stage_name}-{check}"[:48],
                    command         = cmd,
                    description     = ["Test just built components for", stage_name, ":", check],
                    descriptionDone = ["Test just built components for", stage_name, ":", check, "completed"],
                    haltOnFailure   = False, # We want to test as much as we could.
                    env             = stage_env,
                    workdir         = stage_f.obj_dir
                ))

        # Install
        if stage_f.install_dir:
            for target in (install_targets or []):
                stage_f.addStep(
                    steps.CMake(
                        name            = f"install-{stage_name}-{target}"[:48],
                        options         = ["--build", ".", "--target", target],
                        description     = ["Install just built components for", stage_name, ":", target],
                        haltOnFailure   = True,
                        env             = stage_env,
                        workdir         = stage_f.obj_dir
                    ))

        # Normalize root factory in according of the current stage recult factory.
        normalize_factory(f, stage_f)
        # Store the stage factory. We will process them a little bit later.
        stage_factories.append(stage_f)

    # Finalize the result factory.
    f.addSteps([
        # Set up some properties, which could be used to configure the builders.
        steps.SetProperties(
            name            = 'set-props',
            properties      = {
                "depends_on_projects"   : ";".join(f.depends_on_projects),
                "enable_projects"       : ";".join(f.enable_projects),
                "enable_runtimes"       : ";".join(f.enable_runtimes),
                "srcdir"                : util.Interpolate(f.monorepo_dir),
                "srcdir_relative"       : util.Interpolate(LLVMBuildFactory.pathRelativeTo(f.monorepo_dir, f"{obj_root_dir}/stage")),
                "objrootdir"            : util.Interpolate(obj_root_dir),
            }
        ),
    ])

    # Done with all steps for the stage. Now we need to merge these steps into the root factory.
    for stage_f in stage_factories:
        f.addSteps(stage_f.steps)

    return f
