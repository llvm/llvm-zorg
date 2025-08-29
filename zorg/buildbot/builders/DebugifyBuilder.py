from buildbot.plugins import util
from buildbot.steps.shell import ShellCommand
from zorg.buildbot.builders import TestSuiteBuilder
from zorg.buildbot.builders.TestSuiteBuilder import test_suite_build_path
from zorg.buildbot.commands.CmakeCommand import CmakeCommand


def addCheckDebugifyStep(f, debugify_output_path, compiler_dir=".", env={}):
    script = util.Interpolate(
        f"%(prop:builddir)s/{compiler_dir}/llvm/utils/llvm-original-di-preservation.py"
    )
    f.addStep(
        ShellCommand(
            name="check debugify output",
            command=[
                "python3",
                script,
                util.Interpolate(debugify_output_path),
                "--acceptance-test",
                "--reduce",
            ],
            description="check debugify output",
            env=env,
        )
    )


def getDebugifyBuildFactory(
    depends_on_projects=None,
    enable_runtimes="auto",
    targets=None,
    llvm_srcdir=None,
    obj_dir=None,
    checks=None,
    install_dir=None,
    clean=False,
    test_suite_build_flags="-O2 -g -DNDEBUG",
    extra_configure_args=None,
    enable_origin_tracking=True,
    extra_test_suite_configure_args=None,
    env={},
    **kwargs,
):

    # Make a local copy of the LLVM configure args, as we are going to modify that.
    if extra_configure_args is not None:
        llvm_cmake_args = extra_configure_args[:]
    else:
        llvm_cmake_args = list()

    tracking_mode = "COVERAGE_AND_ORIGIN" if enable_origin_tracking else "COVERAGE"
    CmakeCommand.applyRequiredOptions(llvm_cmake_args, [
        ('-DLLVM_ENABLE_DEBUGLOC_COVERAGE_TRACKING=', tracking_mode)
    ])

    # This path will be passed through to util.Interpolate, so we leave it in this format.
    # NB: This must be stored in the test suite build directory, as that is the only way to ensure that it is
    # unconditionally up before (and not after) each run.
    debugify_output_path = f"%(prop:builddir)s/{test_suite_build_path}/debugify-report.json"

    # Make a local copy of the test suite configure args, as we are going to modify that.
    if extra_test_suite_configure_args is not None:
        test_suite_cmake_args = extra_test_suite_configure_args[:]
    else:
        test_suite_cmake_args = list()

    CmakeCommand.applyDefaultOptions(test_suite_cmake_args, [
        ('-DTEST_SUITE_SUBDIRS=', 'CTMark'),
        ('-DTEST_SUITE_RUN_BENCHMARKS=', 'false'),
        ('-DTEST_SUITE_COLLECT_CODE_SIZE=', 'false'),
    ])
    # The only configuration that currently makes sense for Debugify builds is optimized debug info builds; any build
    # configuration adjustments can be made through the test_suite_build_flags arg.
    build_flags = f'{test_suite_build_flags} -Xclang -fverify-debuginfo-preserve -Xclang -fverify-debuginfo-preserve-export={debugify_output_path} -mllvm --debugify-quiet -mllvm -debugify-level=locations'
    CmakeCommand.applyRequiredOptions(test_suite_cmake_args, [
        ('-DCMAKE_BUILD_TYPE=', 'RelWithDebInfo'),
    ])
    test_suite_cmake_args += [
        util.Interpolate(f"-DCMAKE_C_FLAGS_RELWITHDEBINFO={build_flags}"),
        util.Interpolate(f"-DCMAKE_CXX_FLAGS_RELWITHDEBINFO={build_flags}"),
    ]

    f = TestSuiteBuilder.getTestSuiteBuildFactory(
        depends_on_projects=depends_on_projects,
        enable_runtimes=enable_runtimes,
        targets=targets,
        llvm_srcdir=llvm_srcdir,
        obj_dir=obj_dir,
        checks=checks,
        install_dir=install_dir,
        clean=clean,
        extra_configure_args=llvm_cmake_args,
        extra_test_suite_configure_args=test_suite_cmake_args,
        **kwargs
    )

    addCheckDebugifyStep(f, debugify_output_path, compiler_dir=f.monorepo_dir, env=env)

    return f
