# StagedBuilder.py
#
# The factory provides a staged builder configuration to build the LLVM project unified tree.
# 
# Every builder stage includes a pair of cmake configuration and build steps by default.
# The optional steps are the checks (local and remote/custom) and the installation steps.
#
# Also the builder factory accepts the LLVMBuildFactory object prepared by another build factories
# as own build stage.

from buildbot.plugins import steps, util

from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.process.factory import LLVMBuildFactory

import zorg.buildbot.builders.Util as builders_util

# Supported properties:
#   clean                   - clean up the source and the build folders.
#   clean_obj               - clean up the build folders
#
# The single stage arguments:
#   name                    - required: a stage name
#   depends_on_projects     - None or a list of the depended projects.
#   enable_runtimes         - None, "auto" or a list of the runtime projects.
#                             If "auto" is specified, the runtime projects will be extracted from 'depends_on_projects';
#                             otherwise all those projects will go into 'enable_projects' if None is specified
#                             (see LLVMBuildFactory for more details).
#   cmake_definitions       - None or a dictionary of the CMake definitions.
#   cmake_options           - None or a list of the CMake options.
#   targets                 - None (default target) or a list of the targets.
#   checks                  - None (no check) or a list of the check targets.
#   checks_on_target        - None (no target checks) or a list of the target check commands.
#   src_to_build_dir        - None (default: llvm) or a path the project's root inside of the llvm-project directory.
#   install_dir             - the stage install dir. If this argument is specified, the factory will add an installation step
#                             using custom specified `install_target` target or default installation target.
#   install_target          - the stage installation target (default: install)
#   env                     - the stage specific environment.
# VS tools environment variable if using MSVC.
#   vs                      - None, "autodetect", "manual"
#   vs_arch                 - None, "amd64", "x64" & etc.
#
# NOTE: All stages have their own 'obj' directories in format %(prop:builddir)s/build/<stage_name>. It cannot be changed.
#
# The factory sets the following properties to provide more flexible configuration for the builders:
#
#   srcdir                  - relative path to the source code root directory ("llvm-project" by default).
#                             "%(prop:builddir)s/%(prop:srcdir)s" is a full path to the source code dir.
#   srcdir_relative         - relative path from the stage's obj dir to the source code root dir ("../../llvm-project" by default).
#   objrootdir              - relative path to the root obj dir ("build" by default).
#                             "%(prop:builddir)s/%(prop:objrootdir)s/<stage-name>" is a full path to the stage's obj dir.
#   depends_on_projects     - a list of the depended projects for the build.
#   enabled_projects        - a list of enabled projects for all stages.
#   enable_runtimes         - a list of enabled runtimes for all stages.
#

def getCmakeBuildFactory(
        llvm_srcdir = None,         # A custom LLVM src directory within %(prop:builddir)s of the builder.
        generator = "Ninja",        # CMake generator.
        clean = False,              # Do clean build flag.
        stages = [],                # A list of dict() or LLVMBuildFactory() objects that represent the build stages.
        extra_git_args = None,      # Extra parameters for steps.Git step (such as 'config', 'workdir' & etc.)
        jobs = None,                # Restrict a degree of parallelism.
        env  = None,                # Environmental variables for all stages.
    ):

    assert generator, "The CMake generator must be specified."
    assert stages, "At least one stage must be specified."

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

    def normalize_factory(rf, sf):
        # Add extra depended projects to trigger the schedulers.
        if sf.depends_on_projects:
            rf.depends_on_projects = set(rf.depends_on_projects.union(sf.depends_on_projects))
        if sf.enable_runtimes:
            rf.enable_runtimes = frozenset(rf.enable_runtimes.union(sf.enable_runtimes))
            rf.depends_on_projects = set(rf.depends_on_projects.union(sf.enable_runtimes))
        # Update a list of enabled projects for the root factory.
        rf.enable_projects = f.depends_on_projects.difference(f.enable_runtimes)

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
        install_target          = stage.get("install_target", "install")
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
                    name            = f"clean-install-dir-{stage_name}",
                    dir             = util.Interpolate(stage_f.install_dir),
                    haltOnFailure   = False,
                    flunkOnFailure  = False,
                    doStepIf        = lambda step, clean = clean: clean or step.getProperty("clean_obj") == True
                ),
            ])

        stage_f.addStep(
            steps.CMake(
                name            = f"cmake-configure-{stage_name}",
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
        for target in targets:
            cmake_build_options = ["--build", "."]
            if target != ".":
                cmake_build_options.extend(["--target", target])
            if jobs:
                cmake_build_options.extend(["--", "-j", jobs])

            target_title = "default" if target == "." else target

            stage_f.addStep(
                steps.CMake(
                    name            = f"build-{stage_name}-{target_title}",
                    options         = cmake_build_options,
                    description     = ["Build", stage_name, "target", target_title],
                    haltOnFailure   = True,
                    env             = stage_env,
                    workdir         = stage_f.obj_dir
                ))

        # Check Commands.
        for target in checks:
            stage_f.addStep(
                LitTestCommand(
                    name            = f"test-{stage_name}-{target}",
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
                    name            = f"test-{stage_name}-{check}",
                    command         = cmd,
                    description     = ["Test just built components for", stage_name, ":", target],
                    descriptionDone = ["Test just built components for", stage_name, ":", target, "completed"],
                    haltOnFailure   = False, # We want to test as much as we could.
                    env             = stage_env,
                    workdir         = stage_f.obj_dir
                ))

        # Install
        if stage_f.install_dir:
            stage_f.addStep(
                steps.CMake(
                    name            = f"install-all-{stage_name}-{target_title}",
                    options         = ["--build", ".", "--target", install_target],
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
