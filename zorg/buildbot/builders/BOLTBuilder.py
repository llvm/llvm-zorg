from buildbot.plugins import steps
from buildbot.steps.shell import ShellCommand
from zorg.buildbot.builders.UnifiedTreeBuilder import getLLVMBuildFactoryAndSourcecodeSteps, addCmakeSteps, addNinjaSteps
from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.conditions.FileConditions import FileExists
from zorg.buildbot.process.factory import LLVMBuildFactory

def getBOLTCmakeBuildFactory(
           clean = False,
           bolttests = False,
           is_nfc = False,
           targets = None,
           checks = None,
           caches = None,
           extra_configure_args = None,
           env = None,
           depends_on_projects = None,
           **kwargs):

    if env is None:
        env = {'CCACHE_COMPILERCHECK': 'content'}

    bolttests_dir = "bolt-tests"

    cleanBuildRequested = lambda step: clean or step.build.getProperty("clean", default=step.build.getProperty("clean_obj"))
    cleanBuildRequestedByProperty = lambda step: step.build.getProperty("clean")

    if not targets:
        targets = ['bolt']
    if not checks:
        checks = ['check-bolt']

    f = getLLVMBuildFactoryAndSourcecodeSteps(
            depends_on_projects=depends_on_projects,
            **kwargs) # Pass through all the extra arguments.

    if bolttests:
        checks += ['check-large-bolt']
        extra_configure_args += [
            '-DLLVM_EXTERNAL_PROJECTS=bolttests',
            '-DLLVM_EXTERNAL_BOLTTESTS_SOURCE_DIR=' + LLVMBuildFactory.pathRelativeTo(bolttests_dir, f.monorepo_dir),
            ]
        # Clean checkout of bolt-tests if cleanBuildRequested
        f.addSteps([
            steps.RemoveDirectory(name="BOLT tests: clean",
                dir=bolttests_dir,
                haltOnFailure=True,
                warnOnFailure=True,
                doStepIf=cleanBuildRequestedByProperty),

            steps.Git(name="BOLT tests: checkout",
                description="fetching",
                descriptionDone="fetch",
                descriptionSuffix="BOLT Tests",
                repourl='https://github.com/rafaelauler/bolt-tests.git',
                workdir=bolttests_dir,
                alwaysUseLatest=True),
            ])

    # Some options are required for this build no matter what.
    CmakeCommand.applyRequiredOptions(extra_configure_args, [
        ('-G',                      'Ninja'),
        ])

    if caches:
        for cache in caches:
            extra_configure_args += [f"-C../{f.monorepo_dir}/{cache}"]

    addCmakeSteps(
        f,
        cleanBuildRequested=cleanBuildRequested,
        extra_configure_args=extra_configure_args,
        obj_dir=None,
        env=env,
        **kwargs)

    addNinjaSteps(
        f,
        targets=targets,
        checks=checks,
        env=env,
        **kwargs)

    if is_nfc:
        f.addSteps([
            ShellCommand(
                name='nfc-check-setup',
                command=[f"../{f.monorepo_dir}/bolt/utils/nfc-check-setup.py"],
                description=('Setup NFC testing'),
                warnOnFailure=True,
                haltOnFailure=False,
                flunkOnFailure=False,
                env=env),
            ShellCommand(
                name='check-bolt-different',
                command=('find -name timing.log -delete; '
                         'rm -f .llvm-bolt.diff; '
                         'cmp -s bin/llvm-bolt.old bin/llvm-bolt.new || '
                         'touch .llvm-bolt.diff'),
                description=('Check if llvm-bolt binaries are different and '
                             'skip the following nfc-check steps'),
                haltOnFailure=False,
                env=env),
            LitTestCommand(
                name='nfc-check-bolt',
                command=['bin/llvm-lit', '-sv', '-j4',
                         # bolt-info will always mismatch in NFC mode
                         '--xfail=bolt-info.test',
                         'tools/bolt/test'],
                description=["running", "NFC", "check-bolt"],
                descriptionDone=["NFC", "check-bolt", "completed"],
                warnOnFailure=True,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=FileExists('build/.llvm-bolt.diff'),
                env=env),
            LitTestCommand(
                name='nfc-check-large-bolt',
                command=['bin/llvm-lit', '-sv', '-j2',
                         'tools/bolttests'],
                description=["running", "NFC", "check-large-bolt"],
                descriptionDone=["NFC", "check-large-bolt", "completed"],
                warnOnFailure=True,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=FileExists('build/.llvm-bolt.diff'),
                env=env),
            LitTestCommand(
                name='nfc-stat-check',
                command=(f"../{f.monorepo_dir}/bolt/utils/nfc-stat-parser.py "
                         "`find -name timing.log`"),
                description="Check BOLT processing time and max RSS swings",
                warnOnFailure=True,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=FileExists('build/.llvm-bolt.diff'),
                env=env),
            ])

    return f
