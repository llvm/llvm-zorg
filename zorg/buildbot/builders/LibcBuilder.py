from zorg.buildbot.commands.AnnotatedCommand import AnnotatedCommand
from zorg.buildbot.process.factory import LLVMBuildFactory

LIBC_BUILDER_DIR = "libc_builder"
LLVM_ZORG = "%s/llvm-zorg" % LIBC_BUILDER_DIR
ANNOTATED_STEP_RUNNER = (
    "%s/zorg/buildbot/builders/libc/annotated_step_runner.py" % LLVM_ZORG)


def getBuildFactory(clean=False, asan=False, timeout=2400):
    f = LLVMBuildFactory(clean=clean, is_legacy_mode=False,
                         depends_on_projects=["llvm", "libc"])

    # Get llvm-zorg
    f.addGetSourcecodeForProject(
        name='checkout-zorg',
        project='zorg',
        src_dir=LIBC_BUILDER_DIR,
        alwaysUseLatest=True)

    additional_env = {}
    if clean:
        additional_env["BUILDBOT_CLOBBER"] = "1"

    annotated_step_cmd = [ANNOTATED_STEP_RUNNER]
    if clean:
        annotated_step_cmd.append("--clean")
    if asan:
        annotated_step_cmd.append("--asan")

    f.addStep(AnnotatedCommand(name='run_annotated_steps',
                               description=["Run annotated steps"],
                               command=annotated_step_command,
                               haltOnFailure=True,
                               timeout=timeout,
                               env=additional_env))
    return f 
