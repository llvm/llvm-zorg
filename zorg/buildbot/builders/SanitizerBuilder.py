import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN, Git
from buildbot.process.properties import WithProperties
from zorg.buildbot.commands.AnnotatedCommand import AnnotatedCommand

def getSanitizerBuildFactory(
    clean=False,
    env=None,
    timeout=1200):

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        "TERM" : "dumb", # Make sure Clang doesn't use color escape sequences.
                 }
    # Use env variables defined in the system.
    merged_env.update(os.environ)
    # Clobber bot if we need a clean build.
    if clean:
        merged_env["BUILDBOT_CLOBBER"] = "1"
    # Overwrite pre-set items with the given ones, so user can set anything.
    if env is not None:
        merged_env.update(env)

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir=".",
                                               env=merged_env))

    sanitizer_buildbot = "sanitizer_buildbot"
    sanitizer_script_dir = os.path.join(sanitizer_buildbot, "sanitizers")
    # Get sanitizer buildbot scripts.
    f.addStep(SVN(name='svn-sanitizer-buildbot',
                  mode='update',
                  svnurl='http://llvm.org/svn/llvm-project/zorg/trunk/'
                         'zorg/buildbot/builders/sanitizers',
                  workdir=sanitizer_script_dir,
                  alwaysUseLatest=True))

    sanitizer_script = os.path.join("..", sanitizer_script_dir, "buildbot_selector.py")

    # Run annotated command for sanitizer.
    f.addStep(AnnotatedCommand(name="annotate",
                               description="annotate",
                               timeout=timeout,
                               haltOnFailure=True,
                               command="python " + sanitizer_script,
                               env=merged_env))
    return f
