import os

import buildbot
from buildbot.process.properties import WithProperties
from buildbot.steps.shell import SetProperty, ShellCommand
from buildbot.steps.source import SVN
from zorg.buildbot.commands.AnnotatedCommand import AnnotatedCommand
from zorg.buildbot.process.factory import LLVMBuildFactory


def getAnnotatedBuildFactory(
    script,
    clean=False,
    depends_on_projects=None,
    env=None,
    timeout=1200):
    """
    Returns a new build factory that uses AnnotatedCommand, which
    allows the build to be run by version-controlled scripts that do
    not require a buildmaster restart to update.
    """

    f = LLVMBuildFactory(
        depends_on_projects=depends_on_projects,
        llvm_srcdir='llvm.src')

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
    f.addStep(SVN(name='update-annotate-scripts',
                  mode='update',
                  svnurl='http://llvm.org/svn/llvm-project/zorg/trunk/'
                         'zorg/buildbot/builders/annotated',
                  workdir=scripts_dir,
                  alwaysUseLatest=True))

    # Explicitly use '/' as separator, because it works on *nix and Windows.
    script_path = "../%s/%s" % (scripts_dir, script)
    f.addStep(AnnotatedCommand(name="annotate",
                               description="annotate",
                               timeout=timeout,
                               haltOnFailure=True,
                               command=WithProperties(
                                   "python %(script)s --jobs=%(jobs:-)s",
                                   script=lambda _: script_path),
                               env=merged_env))
    return f
