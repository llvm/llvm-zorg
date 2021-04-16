from buildbot.process.properties import WithProperties
from buildbot.steps.shell import SetProperty
from zorg.buildbot.commands.AnnotatedCommand import AnnotatedCommand
from zorg.buildbot.process.factory import LLVMBuildFactory


def getAnnotatedBuildFactory(
    script,
    clean=False,
    depends_on_projects=None,
    env=None,
    extra_args=None,
    timeout=1200,
    checkout_llvm_sources=True,
    script_interpreter="python"):
    """
    Returns a new build factory that uses AnnotatedCommand, which
    allows the build to be run by version-controlled scripts that do
    not require a buildmaster restart to update.

    script: script under "builders/annotated" to be run by python
    clean: set to true for a clean build of llvm
    depends_on_projects: which subprojects to enable
        llvm must be first in the list
        (default: ["llvm", "clang", "compiler-rt", "libcxx",
                   "libcxxabi", "libunwind", "lld"])
    env: environment overrides (map; default is no overrides)
    extra_args: extra arguments to pass to the script (default: [])
    timeout: specifies the builder's timeout in seconds (default: 1200)
    script_interpreter: specifies the interpreter to run scripts (default: "python")
    """

    if depends_on_projects is None:
        depends_on_projects = [
            "llvm",
            "clang",
            "compiler-rt",
            "libcxx",
            "libcxxabi",
            "libunwind",
            "lld"]
    if extra_args is None:
        # We used to add --jobs to all script invocations. Perserve this
        # for cases when the user did not specify extra_args, but allow
        # overriding it if the user did specify extra_args.
        extra_args = [WithProperties("--jobs=%(jobs:-)s")]

    f = LLVMBuildFactory(
        clean=clean,
        depends_on_projects=depends_on_projects)

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
        doStepIf=lambda step: step.build.getProperty('clean', False)))

    merged_env = {
        'TERM': 'dumb'  # Be cautious and disable color output from all tools.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set
        # anything.
        merged_env.update(env)

    scripts_dir = "annotated"

    # Check out zorg so we can run the annotator scripts.
    f.addGetSourcecodeForProject(
        name='update-annotated-scripts',
        project='zorg',
        src_dir='llvm-zorg',
        alwaysUseLatest=True)

    if checkout_llvm_sources:
      f.addGetSourcecodeSteps()

    extra_args_with_props = [WithProperties(arg) for arg in extra_args]
    # Explicitly use '/' as separator, because it works on *nix and Windows.
    if script.startswith('/'):
      command = [script]
    else:
      script_path = "../llvm-zorg/zorg/buildbot/builders/annotated/%s" % (script)
      # Handle scripts with script_interpreter, otherwise execute the script directly.
      if script_interpreter:
        command = [script_interpreter, script_path]
      else:
        command = [script_path]

    command += extra_args_with_props

    f.addStep(AnnotatedCommand(name="annotate",
                               description="annotate",
                               timeout=timeout,
                               haltOnFailure=True,
                               command=command,
                               env=merged_env))
    return f
