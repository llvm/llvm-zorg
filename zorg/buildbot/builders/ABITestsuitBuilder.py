from buildbot.process.properties import WithProperties
from buildbot.steps.source       import SVN

from zorg.buildbot.builders                import ClangBuilder
from zorg.buildbot.commands.LitTestCommand import LitTestCommand

def getABITestsuitBuildFactory(
            always_clean=True,
            test=True,
            cmake='cmake',
            extra_cmake_args=[], # Extra CMake args for all stages.
            jobs=None,

            env={}, # Environmental variables for all steps.

            stage1_config='Release',
            stage2_config='Release'):

    # Prepare environmental variables. Set here all env we want for all steps.
    merged_env = {
        'TERM' : 'dumb' # Make sure Clang doesn't use color escape sequences.
        }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    source_dir       = 'llvm'   # Should match the one used in getClangCMakeBuildFactory.
    stage2_build_dir = 'stage2' # Should match the one defined in getClangCMakeBuildFactory.

    # Bootstrap clang first.
    f = ClangBuilder.getClangCMakeBuildFactory(
            clean=always_clean,
            test=test,
            cmake=cmake,
            extra_cmake_args=extra_cmake_args,
            jobs=jobs,
            env=merged_env,
            useTwoStage=True,
            stage1_config=stage1_config,
            stage2_config=stage2_config)

    # Checkout the test-suite.
    f.addStep(SVN(name='svn-test-suite',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/test-suite/',
                  defaultBranch='trunk',
                  workdir='test-suite'))

    # Run the ABI test.
    abi_test_env = {
        'PYTHONPATH' : WithProperties("%(workdir)s/" + source_dir + "/utils/lit:${PYTHONPATH}"),
        'PATH'       : WithProperties("%(workdir)s/" + stage2_build_dir + "/bin:${PATH}"),
        }
    merged_env.update(abi_test_env)

    abi_test_cmd = ["python", "linux-x86.py", "clang", "test", "-v"]
    if jobs:
        abi_test_cmd.append("-j"+str(jobs))

    f.addStep(LitTestCommand(name='abi-test-suite',
                             command=abi_test_cmd,
                             description=["running", "ABI", "test-suite"],
                             descriptionDone=["ABI", "test-suite", "completed"],
                             workdir='test-suite/ABI-Testsuite',
                             env=merged_env))

    return f
