"""Build Clang on one worker and test it on CUDA GPU workers.

With publish_artifact, getCudaClangBuildFactory hands the toolchain to the
worker's upload command. trigger_scheduler starts getCudaGpuTestFactory, which
fetches the artifact and runs the CUDA test suite and GPU libc tests on a GPU.
"""

import shlex

from buildbot.plugins import steps, util
from buildbot.steps.shell import Test

from zorg.buildbot.builders import TestSuiteBuilder
from zorg.buildbot.builders import UnifiedTreeBuilder

# The runtimes we build for the host as a part of the main build. Note that
# libc is not in this list on purpose: it gets built for the nvptx target only
# (see LLVM_RUNTIME_TARGETS below).
_host_runtimes = ["libcxx", "libcxxabi", "libunwind", "offload", "openmp"]

_gpu_triple = "nvptx64-nvidia-cuda"

# The artifact is the whole installed toolchain, rather than the parts of the build
# tree the GPU builders use: an install is relocatable, and takes no list to keep up
# with what the tests need. Whether to compress it, and how long to keep it, is up to
# the store behind the commands of the workers (see _artifactCommand).
_artifact_name = "clang-cuda"

# The lock on a GPU which builds share (see the 'gpu_lock' argument of
# getCudaGpuTestFactory), named after the GPU's UUID, so that builds on different GPUs
# do not wait for each other. Its count only needs to be greater than the number of
# builds which can share a GPU.
_gpu_lock_max_count = 16


def _getArtifactName():
    # Set by _getArtifactNameStep and passed on to the triggered builders. It is also
    # the name of the local tarball in %(prop:builddir)s.
    return _requiredProperty.withArgs("artifact")


@util.renderer
def _requiredProperty(props, name):
    """Return a build property, failing if it is unset or empty."""
    value = props.getProperty(name)
    if value is None or value == "":
        raise ValueError(f"the '{name}' property is not set")
    return value


@util.renderer
def _requiredWorkerInfo(props, name):
    """Return a required worker info value without surrounding whitespace."""
    value = props.getBuild().getWorkerInfo().getProperty(name)
    if value is None or value.strip() == "":
        raise ValueError(f"the worker's info/{name} is not set")
    return value.strip()


@util.renderer
def _gpuLock(props, mode):
    """Return the GPU lock in the given mode, after _getGpuUuidStep has run."""
    uuid = props.getProperty("gpu_uuid")
    if uuid is None or uuid == "":
        raise ValueError("the 'gpu_uuid' property is not set")
    # One UUID per line, for each GPU the worker sees.
    uuids = uuid.split()
    if len(uuids) != 1:
        raise ValueError(f"the worker sees {len(uuids)} GPUs ({', '.join(uuids)}) rather than one")
    return [util.MasterLock(f"gpu-{uuid}", maxCount = _gpu_lock_max_count).access(mode)]


def _withGpuLock(f, mode):
    """Lock the factory's GPU test steps in the given mode and return it."""
    for s in f.steps:
        if issubclass(s.step_class, Test):
            s.kwargs["locks"] = _gpuLock.withArgs(mode)
    return f


@util.renderer
def _artifactCommand(_props, command):
    """Append the artifact name to a worker command, splitting strings as shell args."""
    if isinstance(command, str):
        command = shlex.split(command)
    return list(command) + [_getArtifactName()]


def _getArtifactNameStep():
    """Name the artifact after its revision and build number to avoid overwrites."""
    return steps.SetProperties(
        name            = "set-props-artifact",
        properties      = {
            "artifact"  : util.Interpolate(
                f"{_artifact_name}-%(prop:got_revision)s-b%(prop:buildnumber)s.tar"),
        }
    )


class _CudaDirs:
    """Directory layout shared by both factories; *_path attributes are renderables."""
    def __init__(self):
        self.obj_dir            = "build"
        self.toolchain_dir      = "toolchain"
        self.test_suite_src_dir = "llvm-test-suite"
        self.test_suite_obj_dir = "build-tests"
        self.libc_obj_dir       = "build-libc"
        self.install_dir        = "install"

        self.builddir_path      = util.Interpolate("%(prop:builddir)s")
        # Where the GPU builders unpack the toolchain artifact.
        self.toolchain_path     = util.Interpolate(f"%(prop:builddir)s/{self.toolchain_dir}")
        self.gpu_loader         = util.Interpolate(f"%(prop:builddir)s/{self.toolchain_dir}/bin/llvm-gpu-loader")
        # Unlike a generated llvm-lit, lit of the source tree works with any toolchain.
        self.source_lit         = util.Interpolate("%(prop:builddir)s/llvm-project/llvm/utils/lit/lit.py")
        self.externals_path     = _requiredWorkerInfo.withArgs("test_suite_externals")


def getCudaClangBuildFactory(
        depends_on_projects = None,
        publish_artifact = False,
        trigger_scheduler = None,
        upload_command = None,
        jobs = None,
        cmake_definitions = None,
        clean = False,
        env  = None,
    ):
    """Create a factory to build Clang for the GPU test builders.

    This worker needs no GPU or CUDA toolkit. It builds Clang and the nvptx
    runtimes without running tests; optionally it publishes the toolchain and
    triggers getCudaGpuTestFactory. It needs git, CMake, Ninja, a C/C++
    compiler, lld, python3 with pyyaml, and tar when publishing.

    Buildbot's clean and clean_obj properties clean the source and build
    folders. If jobs is omitted, the worker must set the jobs property.

    Args:
        depends_on_projects: List of LLVM projects to schedule builds for;
            defaults to the projects built by this factory.
        publish_artifact: Bool; upload the installed toolchain.
        trigger_scheduler: String name of a Triggerable scheduler; requires
            publish_artifact.
        upload_command: List or string of upload command arguments; defaults
            to the worker's info/artifact_upload_command when publishing.
            The artifact name is appended to the command.
        jobs: Integer build parallelism; defaults to the worker's jobs property.
        cmake_definitions: Dict of additional CMake definitions; overrides defaults.
        clean: Bool; always do a clean build.
        env: Dict of environment variables for all steps.

    Returns:
        The configured build factory.
    """
    if bool(trigger_scheduler):
        assert bool(publish_artifact), \
            "The 'publish_artifact' argument must be specified when 'trigger_scheduler' is specified."

    if depends_on_projects is None:
        depends_on_projects = [
            "clang",
            "libc",
            "libcxx",
            "libcxxabi",
            "libunwind",
            "llvm",
            "offload",
            "openmp",
        ]

    if jobs is None:
        jobs = _requiredProperty.withArgs("jobs")

    dirs = _CudaDirs()
    env = dict(env or {})

    definitions = {
        "CMAKE_BUILD_TYPE"                  : "Release",
        "LLVM_ENABLE_ASSERTIONS"            : "ON",
        "LLVM_USE_LINKER"                   : "lld",
        # FileCheck, count and not, which the lit configurations of the tests expect.
        "LLVM_INSTALL_UTILS"                : "ON",
        # Host and device code only: the other backends are a third of the build.
        "LLVM_TARGETS_TO_BUILD"             : "Native;NVPTX",
        "CLANG_ENABLE_STATIC_ANALYZER"      : "OFF",
        # The nvptx runtimes, which the stand-alone GPU libc build needs.
        "LLVM_RUNTIME_TARGETS"              : f"default;{_gpu_triple}",
        f"RUNTIMES_{_gpu_triple}_LLVM_ENABLE_RUNTIMES" : "libc",
        # The GPU builder runs the libc tests. Asking for them here would also warn
        # that there is no GPU, as libc probes -march=native for the test architecture.
        f"RUNTIMES_{_gpu_triple}_LLVM_INCLUDE_TESTS" : "OFF",
    }
    definitions.update(cmake_definitions or {})

    # After the checkout, which sets got_revision.
    pre_configure_steps = [
        _getArtifactNameStep(),
    ]

    post_finalize_steps = []
    if publish_artifact:
        if upload_command is None:
            upload_command = _requiredWorkerInfo.withArgs("artifact_upload_command")
        post_finalize_steps.extend(
            _getPublishArtifactSteps(
                upload_command      = upload_command,
                dirs                = dirs,
                env                 = env,
            )
        )
    if trigger_scheduler:
        post_finalize_steps.extend(
            _getTriggerSteps(trigger_scheduler = trigger_scheduler)
        )

    return UnifiedTreeBuilder.getCmakeExBuildFactory(
        depends_on_projects = depends_on_projects,
        enable_projects     = ["clang"],
        enable_runtimes     = _host_runtimes,
        clean               = clean,
        # No tests here. The GPU test builders run them (see getCudaGpuTestFactory).
        checks              = None,
        targets             = ["."],
        install_targets     = ["install"],
        cmake_definitions   = definitions,
        obj_dir             = dirs.obj_dir,
        install_dir         = dirs.install_dir,
        jobs                = jobs,
        env                 = dict(env),
        pre_configure_steps = pre_configure_steps,
        post_build_steps    = [],
        # Install afresh, so that what an earlier revision installed does not ship.
        pre_install_steps   = [
            steps.RemoveDirectory(
                name            = "remove-previous-install",
                dir             = dirs.install_dir,
                haltOnFailure   = True,
            ),
        ],
        post_finalize_steps = post_finalize_steps,
    )


def getCudaGpuTestFactory(
        test_suite = False,
        gpu_libc = False,
        gpu_lock = False,
        gpu_arch = None,
        cuda_test_jobs = 4,
        download_command = None,
        jobs = None,
        env  = None,
    ):
    """Create a factory to test a Clang toolchain on a GPU worker.

    A Triggerable scheduler supplies the artifact and got_revision properties;
    this factory fetches that toolchain and checks out the triggering revision.
    It needs a driver and nvidia-smi, git, CMake, Ninja, python3, and tar.
    The test suite also needs CUDA toolkits and GCC in the worker's
    directory named by info/test_suite_externals; GPU libc needs pyyaml and ptxas.
    Force the triggering builder to create a build with a new artifact.
    Select at least one test stage.

    Args:
        test_suite: Bool; run the LLVM test suite's CUDA tests.
        gpu_libc: Bool; run GPU libc tests (requires sm_60 or newer).
        gpu_lock: Bool; lock the GPU for tests on shared workers. CUDA assert tests
            take it exclusively; libc tests share it. Requires exactly one GPU.
        gpu_arch: String GPU architecture, e.g. "sm_75"; defaults to info/gpu_arch.
        cuda_test_jobs: Integer parallelism for CUDA tests.
        download_command: List or string of download command arguments; defaults
            to info/artifact_download_command. The artifact name is appended.
        jobs: Integer build parallelism; defaults to the worker's jobs property.
        env: Dict of environment variables for all steps.

    Returns:
        The configured test factory.
    """
    assert test_suite or gpu_libc, \
        "At least one of the 'test_suite' and 'gpu_libc' arguments must be specified."

    if download_command is None:
        download_command = _requiredWorkerInfo.withArgs("artifact_download_command")

    if gpu_arch is None:
        gpu_arch = _requiredWorkerInfo.withArgs("gpu_arch")
    if jobs is None:
        jobs = _requiredProperty.withArgs("jobs")

    dirs = _CudaDirs()
    env = dict(env or {})

    f = UnifiedTreeBuilder.getLLVMBuildFactoryAndPrepareForSourcecodeSteps(
        depends_on_projects = [],
        enable_projects     = [],
        enable_runtimes     = [],
    )
    # Before the llvm-project checkout, which then sets got_revision to the revision
    # under test rather than leaving it at the test suite's.
    if test_suite:
        _addCudaTestSuiteCheckoutSteps(f, dirs)
    f.addGetSourcecodeSteps()

    f.addStep(_getGpuInfoStep(dirs, env))
    if gpu_lock:
        f.addStep(_getGpuUuidStep(dirs, env))
    f.addStep(_getFetchArtifactStep(download_command, dirs, env))

    if test_suite:
        f.addSteps(
            _getCudaTestSuiteSteps(
                gpu_arch        = gpu_arch,
                cuda_test_jobs  = cuda_test_jobs,
                gpu_lock        = gpu_lock,
                jobs            = jobs,
                dirs            = dirs,
                env             = env,
            ).steps)

    if gpu_libc:
        f.addSteps(
            _getGpuLibcSteps(
                gpu_arch            = gpu_arch,
                gpu_lock            = gpu_lock,
                jobs                = jobs,
                dirs                = dirs,
                env                 = env,
            ).steps)

    return f


def _getGpuInfoStep(dirs, env):
    """Report the GPU about to run tests, failing early if there is none."""
    return steps.ShellCommand(
        name            = "gpu-info",
        command         = ["nvidia-smi", "-L"],
        description     = ["GPU information"],
        haltOnFailure   = True,
        env             = dict(env),
        workdir         = dirs.builddir_path,
    )


def _getGpuUuidStep(dirs, env):
    """Set gpu_uuid for the GPU lock; _gpuLock rejects workers with multiple GPUs."""
    return steps.SetPropertyFromCommand(
        name            = "set-props-gpu-uuid",
        command         = ["nvidia-smi", "--query-gpu=uuid", "--format=csv,noheader"],
        property        = "gpu_uuid",
        description     = ["Get the GPU UUID"],
        haltOnFailure   = True,
        env             = dict(env),
        workdir         = dirs.builddir_path,
    )


def _getPublishArtifactSteps(upload_command, dirs, env):
    """Return steps to pack and upload the toolchain."""
    return [
        steps.ShellSequence(
            name            = "publish-artifact",
            commands        = [
                # Tarballs left behind by builds which failed before they uploaded.
                util.ShellArg(
                    command         = f"rm -f {_artifact_name}-*.tar",
                    logname         = "stdio",
                    haltOnFailure   = True),
                util.ShellArg(
                    command         = ["tar", "-cf", _getArtifactName(), "-C", dirs.install_dir, "."],
                    logname         = "stdio",
                    haltOnFailure   = True),
                util.ShellArg(
                    command         = _artifactCommand.withArgs(upload_command),
                    logname         = "stdio",
                    haltOnFailure   = True),
                util.ShellArg(
                    command         = util.Interpolate(
                        'rm -f "%(kw:artifact)s"',
                        artifact = _getArtifactName()),
                    logname         = "stdio",
                    haltOnFailure   = True),
            ],
            description     = ["Publish the toolchain artifact"],
            haltOnFailure   = True,
            env             = dict(env),
            workdir         = dirs.builddir_path,
        ),
    ]


def _getTriggerSteps(trigger_scheduler):
    """Return steps to trigger the GPU test builder."""
    return [
        steps.Trigger(
            name                = "trigger-gpu-tests",
            schedulerNames      = [trigger_scheduler],
            # Test the revision we have just built, with the artifact of this build.
            updateSourceStamp   = True,
            set_properties      = {
                "artifact"      : util.Property("artifact"),
            },
            # The GPU builds report for themselves.
            waitForFinish       = False,
        ),
    ]


def _getFetchArtifactStep(download_command, dirs, env):
    """Fetch the triggering build's toolchain and discard stale build directories."""
    return steps.ShellSequence(
        name            = "fetch-artifact",
        commands        = [
            # A stale toolchain file would mask an incomplete artifact. The test build
            # directories go too: ninja tracks the path of the compiler, not the
            # compiler, so it would rerun what the previous toolchain built.
            util.ShellArg(
                command         = ["rm", "-rf",
                                   dirs.toolchain_dir,
                                   dirs.test_suite_obj_dir,
                                   dirs.libc_obj_dir],
                logname         = "stdio",
                haltOnFailure   = True),
            util.ShellArg(
                command         = _artifactCommand.withArgs(download_command),
                logname         = "stdio",
                haltOnFailure   = True),
            util.ShellArg(
                command         = ["mkdir", dirs.toolchain_dir],
                logname         = "stdio",
                haltOnFailure   = True),
            util.ShellArg(
                command         = ["tar", "-xf", _getArtifactName(), "-C", dirs.toolchain_dir],
                logname         = "stdio",
                haltOnFailure   = True),
            util.ShellArg(
                command         = util.Interpolate(
                    'rm -f "%(kw:artifact)s"',
                    artifact = _getArtifactName()),
                logname         = "stdio",
                haltOnFailure   = True),
        ],
        description     = ["Fetch the toolchain artifact"],
        haltOnFailure   = True,
        env             = dict(env),
        workdir         = dirs.builddir_path,
    )


def _addCudaTestSuiteCheckoutSteps(f, dirs):
    """Add steps to check out the latest LLVM test suite."""
    src_path = f"%(prop:builddir)s/{dirs.test_suite_src_dir}"

    f.addStep(steps.RemoveDirectory(
        name            = "clean-src-dir-cuda-test-suite",
        dir             = util.Interpolate(src_path),
        haltOnFailure   = False,
        flunkOnFailure  = False,
        doStepIf        = lambda step: bool(step.getProperty("clean")),
    ))
    f.addGetSourcecodeForProject(
        project         = "test-suite",
        name            = "checkout-cuda-test-suite",
        src_dir         = src_path,
        alwaysUseLatest = True,
    )


def _getCudaTestSuiteSteps(
        gpu_arch,
        cuda_test_jobs,
        gpu_lock,
        jobs,
        dirs,
        env,
    ):
    """Return a factory to build and run the LLVM test suite's CUDA tests."""
    definitions = {
        "CUDA_GPU_ARCH"                     : gpu_arch,
        "CUDA_JOBS"                         : cuda_test_jobs,
        "CUDA_NEW_DRIVER"                   : "OFF",
        "TEST_SUITE_COLLECT_CODE_SIZE"      : "OFF",
        "TEST_SUITE_COLLECT_COMPILE_TIME"   : "OFF",
        "TEST_SUITE_EXTERNALS_DIR"          : dirs.externals_path,
        "TEST_SUITE_LIT_FLAGS"              : "-vv",
        "TEST_SUITE_LIT:FILEPATH"           : dirs.source_lit,
        "TEST_SUITE_SUBDIRS"                : "External",
    }

    test_suite = TestSuiteBuilder.getLlvmTestSuiteSteps(
        hint                = "cuda-test-suite",
        # Checked out up front (see _addCudaTestSuiteCheckoutSteps).
        repo_profiles       = None,
        src_dir             = dirs.test_suite_src_dir,
        obj_dir             = dirs.test_suite_obj_dir,
        targets             = ["cuda-tests-simple"],
        checks              = ["check-cuda-simple"],
        compiler_dir        = dirs.toolchain_path,
        cmake_definitions   = definitions,
        jobs                = jobs,
        env                 = dict(env),
    )

    # These tests include the assert tests, which fault the GPU (see 'gpu_lock' in
    # getCudaGpuTestFactory).
    return _withGpuLock(test_suite, "exclusive") if gpu_lock else test_suite


def _getGpuLibcSteps(
        gpu_arch,
        gpu_lock,
        jobs,
        dirs,
        env,
    ):
    """Return a factory to build the GPU libc and run its tests on the GPU."""
    libc = UnifiedTreeBuilder.getCmakeExBuildFactory(
        depends_on_projects     = ["libc", "llvm"],
        enable_projects         = [],
        enable_runtimes         = ["libc"],
        hint                    = "nvptx-libc",
        # The source tree is the one checked out at the start of the build.
        repo_profiles           = None,
        allow_cmake_defaults    = False,
        src_to_build_dir        = "runtimes",
        obj_dir                 = dirs.libc_obj_dir,
        # Compile the tests up front, so that the check step only runs them on the GPU.
        targets                 = ["libc", "check-libc-build"],
        checks                  = ["check-libc"],
        install_targets         = None,
        cmake_definitions       = {
            "CMAKE_BUILD_TYPE"              : "Release",
            "CMAKE_C_COMPILER"              : util.Interpolate("%(kw:dir)s/bin/clang", dir = dirs.toolchain_path),
            "CMAKE_C_COMPILER_TARGET"       : _gpu_triple,
            "CMAKE_C_COMPILER_WORKS"        : "TRUE",
            "CMAKE_CXX_COMPILER"            : util.Interpolate("%(kw:dir)s/bin/clang++", dir = dirs.toolchain_path),
            "CMAKE_CXX_COMPILER_TARGET"     : _gpu_triple,
            "CMAKE_CXX_COMPILER_WORKS"      : "TRUE",
            "CMAKE_CROSSCOMPILING_EMULATOR" : dirs.gpu_loader,
            # Otherwise libc probes -march=native for the GPU, and builds no tests at all
            # when that fails, which check-libc reports as a pass.
            "LIBC_GPU_TEST_ARCHITECTURE"    : gpu_arch,
            "LLVM_BINARY_DIR"               : dirs.toolchain_path,
            "LLVM_DEFAULT_TARGET_TRIPLE"    : _gpu_triple,
            "LLVM_RUNTIMES_TARGET"          : _gpu_triple,
        },
        jobs                    = jobs,
        env                     = dict(env),
    )

    return _withGpuLock(libc, "counting") if gpu_lock else libc
