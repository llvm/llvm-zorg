# TODO: Change WithProperties to Interpolate
from buildbot.process.properties import WithProperties
from zorg.buildbot.commands.AnnotatedCommand import AnnotatedCommand
from zorg.buildbot.process.factory import LLVMBuildFactory

def getSanitizerBuildFactory(
    clean=False,
    extra_depends_on_projects=[],
    extra_configure_args=None,
    env=None,
    timeout=1200):

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        "TERM" : "dumb", # Make sure Clang doesn't use color escape sequences.
                 }
    # Clobber bot if we need a clean build.
    if clean:
        merged_env["BUILDBOT_CLOBBER"] = "1"
    # Overwrite pre-set items with the given ones, so user can set anything.
    if env is not None:
        merged_env.update(env)

    depends_on_projects = [
        "llvm",
        "clang",
        "compiler-rt",
        "libcxx",
        "libcxxabi",
        "libunwind",
        "lld",
    ] + extra_depends_on_projects

    if extra_configure_args:
        extra_configure_args = ['--'] + list(extra_configure_args)
    else:
        extra_configure_args = []

    # Explicitly use '/' as separator, because it works on *nix and Windows.
    sanitizer_script_dir = "sanitizer_buildbot/sanitizers"
    sanitizer_script = "../%s/zorg/buildbot/builders/sanitizers/%s" % (sanitizer_script_dir, "buildbot_selector.py")

    f = LLVMBuildFactory(
        clean=clean,
        depends_on_projects=depends_on_projects,
        llvm_srcdir=sanitizer_script_dir)

    # Get sanitizer buildbot scripts.
    f.addGetSourcecodeForProject(
        name='update-annotate-scripts',
        project='zorg',
        src_dir=sanitizer_script_dir,
        alwaysUseLatest=True)

    # Run annotated command for sanitizer.
    command = ['python', sanitizer_script] + extra_configure_args
    f.addStep(AnnotatedCommand(name="annotate",
                               description="annotate",
                               timeout=timeout,
                               haltOnFailure=True,
                               command=command,
                               env=merged_env))
    return f
