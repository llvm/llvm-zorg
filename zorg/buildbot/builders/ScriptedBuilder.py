import os

from buildbot.plugins import steps, util

from zorg.buildbot.commands.AnnotatedCommand import AnnotatedCommand
from zorg.buildbot.process.factory import LLVMBuildFactory


def getScriptedBuildFactory(
    scriptpath,
    *scriptargs,
    depends_on_projects,
    env=None,
    timeout=1200,
    script_interpreter="python",
    warnOnWarnings=False,
    **kwargs,
):
    assert scriptpath, "Must specify a script the worker is going to execute"
    assert (
        depends_on_projects
    ), "Must specify a set of projects; any change one of those projects will trigger a worker run"

    llvm_srcdir = "llvm.src"

    # If true, clean everything, including source dirs
    def cleanBuildRequested(step):
        return step.build.getProperty("clean")

    f = LLVMBuildFactory(
        depends_on_projects=depends_on_projects, llvm_srcdir=llvm_srcdir
    )

    # When cleaning, delete the source directory; everything should be deleted
    # by the build script itself.
    f.addStep(
        steps.RemoveDirectory(
            name="clean-srcdir",
            dir=f.monorepo_dir,
            warnOnFailure=True,
            doStepIf=cleanBuildRequested,
        )
    )

    # Checkout the llvm-project repository
    f.addGetSourcecodeSteps(**kwargs)

    # Prepare running the build script
    command = [
        script_interpreter,
        os.path.join(
            "..", f.monorepo_dir, scriptpath
        ),  # Location of the build script is relative to the llvm-project checkout
        f"--workdir=.",  # AnnotatedCommand executes the script with build/ as cwd
    ]

    # Add any user-defined command line switches
    command += [util.Interpolate(arg) for arg in scriptargs]

    merged_env = {
        "TERM": "dumb"  # Be cautious and disable color output from all tools.
    }
    for k, v in env or {}:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env[k] = util.Interpolate(v)

    f.addStep(
        AnnotatedCommand(
            name="annotate",
            description="Run build script",
            timeout=timeout,
            haltOnFailure=True,
            warnOnWarnings=warnOnWarnings,
            command=command,
            env=merged_env,
        )
    )

    return f
