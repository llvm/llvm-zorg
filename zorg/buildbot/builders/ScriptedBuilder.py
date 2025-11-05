from buildbot.plugins import util
from buildbot.steps.shell import SetProperty
from zorg.buildbot.commands.AnnotatedCommand import AnnotatedCommand
from zorg.buildbot.process.factory import LLVMBuildFactory
from buildbot.steps.shell import ShellCommand, WarningCountingShellCommand
from buildbot.plugins import steps, util
from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.process.factory import LLVMBuildFactory
import os

def getScriptedBuildFactory(scriptpath,  *scriptargs,    clean=False,
	    depends_on_projects=None,
	    env=None,
	    extra_args=None,
	    timeout=1200,
	    #checkout_llvm_sources=True,
	    script_interpreter="python",
	    warnOnWarnings=False, **kwargs):

    llvm_srcdir = "llvm.src"
    venvpath = "bbenv"

    # If true, clean everything, including source dirs
    def cleanBuildRequested(step):
        return step.build.getProperty("clean")
    # If true, clean build products; implied if cleanBuildRequested is true
    def cleanObjRequested(step):
        return cleanBuildRequested(step) or clean or step.build.getProperty("clean_obj")

    if depends_on_projects is None:
        depends_on_projects = [
            "llvm",
            "clang",
            "compiler-rt",
            "libcxx",
            "libcxxabi",
            "libunwind",
            "lld"]


    f = LLVMBuildFactory(
         depends_on_projects=depends_on_projects,
        clean=clean,
        llvm_srcdir=llvm_srcdir,
        cleanBuildRequested=cleanBuildRequested      )

    f.addStep(steps.RemoveDirectory(name='clean-src-dir',
                           dir=f.monorepo_dir,
                           warnOnFailure=True,
                           doStepIf=cleanBuildRequested))

    f.addStep(steps.RemoveDirectory(name='clean-venv-dir',
                           dir=venvpath,
                           warnOnFailure=True,
                           doStepIf=cleanBuildRequested))

    # Get the source code.
    f.addGetSourcecodeSteps(**kwargs)

    if clean:
        f.addStep(SetProperty(property='clean', command='echo 1'))

    # We normally use the clean property to indicate that we want a
    # clean build, but AnnotatedCommand uses the clobber property
    # instead. Therefore, set clobber if clean is set to a truthy
    # value.  This will cause AnnotatedCommand to set
    # BUILDBOT_CLOBBER=1 in the environment, which is how we
    # communicate to the script that we need a clean build.
    f.addStep(SetProperty(
        property='clobber',
        command='echo 1',
        doStepIf=cleanObjRequested))

    merged_env = {
        'TERM': 'dumb'  # Be cautious and disable color output from all tools.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set
        # anything.
        merged_env.update(env)


    f.addStep(ShellCommand(
          #  name="create-venv",
            command=[script_interpreter, "-m", "venv", venvpath], # " --upgrade", "--upgrade-deps",
          #  description="Create a venv"
    ))
    venv_interpreter = os.path.join(venvpath, 'bin', 'python')

    extra_args_with_props = [util.Interpolate(arg) for arg in scriptargs]

    command = [venv_interpreter, os.path.join('..', f.monorepo_dir, scriptpath)] # relative to build path
    command += extra_args_with_props

    f.addStep(AnnotatedCommand(name="annotate",
                               description="annotate",
                               timeout=timeout,
                               haltOnFailure=True,
                               warnOnWarnings=warnOnWarnings,
                               command=command,
                               env=merged_env))

    return f
