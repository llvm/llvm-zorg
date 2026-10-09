# CudaBuilder.py
#
# Factories for CUDA builders which build Clang on one worker and test it on others,
# with a GPU.
#
# getCudaClangBuildFactory() builds Clang with the nvptx runtimes and runs no tests at all.
#
# Passing 'publish_artifact' to it packs the just built toolchain and hands it to the
# worker's upload command, and 'trigger_scheduler' starts the test builder (see
# getCudaGpuTestFactory), which fetches it back and does all the GPU work. That keeps
# the long Clang build off the GPU workers.
#
# getCudaGpuTestFactory() fetches the toolchain of the triggering build with the
# worker's download command and runs the stages its builder asks for against it, on the
# GPU: the CUDA tests of the LLVM test suite, the GPU libc tests and NVIDIA's CUDA
# library samples.

import os
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

# NVIDIA's public CUDA library samples, pinned so that their results only change with
# the compiler. Their GPU code is NVIDIA's, inside the prebuilt libraries, so they test
# Clang building programs against the toolkits rather than its device code generation.
# Which of them run is up to _cuda_library_samples_superbuild.
_cuda_library_samples_repo = "https://github.com/NVIDIA/CUDALibrarySamples.git"
_cuda_library_samples_revision = "07c4f09223302ce4310eef945ed458e092598d17"

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

    """ The value of a property the build cannot do without. An unset property would
        render as None, which the commands and the CMake definitions take as a value.
    """

    value = props.getProperty(name)
    if value is None or value == "":
        raise ValueError(f"the '{name}' property is not set")
    return value


@util.renderer
def _requiredWorkerInfo(props, name):

    """ The contents of a file in the info/ directory of the worker, which describe the
        worker to the master, and which the build cannot do without.
    """

    value = props.getBuild().getWorkerInfo().getProperty(name)
    if value is None or value.strip() == "":
        raise ValueError(f"the worker's info/{name} is not set")
    return value.strip()


@util.renderer
def _gpuLock(props, mode):

    """ The lock on the GPU of the worker (see _gpu_lock_max_count), taken in the given
        mode: "exclusive" or "counting". The build must have run _getGpuUuidStep.
    """

    uuid = props.getProperty("gpu_uuid")
    if uuid is None or uuid == "":
        raise ValueError("the 'gpu_uuid' property is not set")
    # One UUID per line, for each GPU the worker sees.
    uuids = uuid.split()
    if len(uuids) != 1:
        raise ValueError(f"the worker sees {len(uuids)} GPUs ({', '.join(uuids)}) rather than one")
    return [util.MasterLock(f"gpu-{uuid}", maxCount = _gpu_lock_max_count).access(mode)]


def _withGpuLock(f, mode):

    """ Make the test steps of the factory take the lock on the GPU in the given mode.
        The test steps of the factories of TestSuiteBuilder and UnifiedTreeBuilder are
        their check steps, which run on the GPU here.

        Returns the factory.
    """

    for s in f.steps:
        if issubclass(s.step_class, Test):
            s.kwargs["locks"] = _gpuLock.withArgs(mode)
    return f


@util.renderer
def _artifactCommand(_props, command):

    """ The worker's command which uploads or downloads the toolchain artifact, so that
        nothing here depends on the store behind it: a list, or a string to split like a
        shell would. It runs in %(prop:builddir)s with the name of the artifact, which is
        also the name of the local tarball, as its last argument:

            upload      Store the tarball, replacing any object of that name.
            download    Write the object to the tarball, failing when there is none or
                        when it does not match what was uploaded.

        The command checks the integrity of the transfer, and fails with a non-zero status.
    """

    if isinstance(command, str):
        command = shlex.split(command)
    return list(command) + [_getArtifactName()]


def _getArtifactNameStep():

    """ Name the toolchain artifact after the revision and the build it comes from, so
        that neither another revision nor a rebuild of this one replaces an artifact a GPU
        builder may still be fetching.
    """

    return steps.SetProperties(
        name            = "set-props-artifact",
        properties      = {
            "artifact"  : util.Interpolate(
                f"{_artifact_name}-%(prop:got_revision)s-b%(prop:buildnumber)s.tar"),
        }
    )


class _CudaDirs:

    """ The directory layout the two CUDA factories share. The '*_path' attributes are
        renderables, resolved against the build directory when the build runs.
    """

    def __init__(self):
        self.obj_dir            = "build"
        self.toolchain_dir      = "toolchain"
        self.test_suite_src_dir = "llvm-test-suite"
        self.test_suite_obj_dir = "build-tests"
        self.libc_obj_dir       = "build-libc"
        self.samples_src_dir    = "CUDALibrarySamples"
        self.superbuild_dir     = "library-samples-superbuild"
        self.samples_obj_dir    = "build-library-samples"
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

    """ Create and configure a builder factory to build Clang for the GPU test builders
        (see getCudaGpuTestFactory).

        A single CMake build of Clang with the nvptx runtimes, which runs no tests, so the
        worker needs neither a GPU nor a CUDA toolkit. It needs git, CMake, Ninja, a host
        C/C++ compiler, lld (the default LLVM_USE_LINKER, which 'cmake_definitions' can
        override), python3 with pyyaml for the libc header generator, and tar to publish
        the artifact.

        Passing 'publish_artifact' packs the just built toolchain and hands it to the
        worker's upload command, and 'trigger_scheduler' starts the builder which fetches
        it back and runs the test stages on a worker with a GPU (see getCudaGpuTestFactory).

        Property Parameters
        -------------------

        clean : boolean
            Clean up the source and the build folders.

        clean_obj : boolean
            Clean up the build folders.

        jobs : int
            The degree of parallelism of the builds. Used as a default value of the
            'jobs' argument. When the builder does not pass that argument, the worker
            must set this property, or the build fails.

        Worker Info
        -----------

        The files in the info/ directory of the worker which the build reads.

        artifact_upload_command
            The command which uploads the toolchain artifact (see _artifactCommand).
            Used as a default value of the 'upload_command' argument. When the builder
            does not pass that argument, the worker must provide this file, or the
            publish step fails.


        Parameters
        ----------

        depends_on_projects : list, optional
            A list of the LLVM projects this builder depends on.

        publish_artifact : boolean
            Pack the just built toolchain and upload it with the upload command
            (default is False).

        trigger_scheduler : str, optional
            A name of the Triggerable scheduler of the GPU test builder (default is None).

            Requires the 'publish_artifact' argument: there would be nothing for the
            triggered builder to fetch otherwise. Publishing without triggering is fine.

        upload_command : list, optional
            The command which uploads the toolchain artifact, given its name as the last
            argument (default is the worker's info/artifact_upload_command).

            Required by the 'publish_artifact' argument.

        jobs : int, optional
            The degree of parallelism of the builds
            (default is the 'jobs' property of the worker).

        cmake_definitions : dict, optional
            Extra CMake definitions for the main build (default is None).

            These definitions override the defaults of this factory.

        clean : boolean
            Always do a clean build (default is False).

        env : dict, optional
            Common environmental variables for all build steps (default is None).

        Returns
        -------

        Returns the factory object with the prepared build steps.

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
        library_samples = False,
        gpu_lock = False,
        gpu_arch = None,
        cuda_test_jobs = 4,
        download_command = None,
        jobs = None,
        env  = None,
    ):

    """ Create and configure a builder factory to run the CUDA tests, the GPU libc tests
        and the samples of NVIDIA's prebuilt libraries against a Clang toolchain built by
        another builder (see getCudaClangBuildFactory).

        It fetches the toolchain artifact of the triggering build, so the GPU worker never
        builds Clang, and runs these stages against it:

            1. The CUDA tests of the LLVM test suite, compiled by the unpacked Clang and
               executed on the GPU (see TestSuiteBuilder).
            2. A stand-alone runtimes build of the GPU libc, executed on the GPU through
               llvm-gpu-loader (see UnifiedTreeBuilder.getCmakeExBuildFactory).
            3. NVIDIA's public samples of its prebuilt CUDA libraries, compiled by the
               unpacked Clang against every recent enough toolkit of the worker, and
               executed on the GPU.

        A stage only runs when its argument asks for it ('test_suite', 'gpu_libc' and
        'library_samples'), and at least one must, so that a builder names what it tests.

        The worker needs the NVIDIA driver and nvidia-smi, git, CMake, Ninja, python3 and
        tar, and for each stage:

            test_suite      The CUDA toolkits and GCC installations of its test suite
                            externals directory (see 'test_suite_externals' below).
            gpu_libc        python3 with pyyaml for the libc header generator, and the
                            ptxas of a CUDA toolkit, which clang assembles the nvptx64
                            code with. It finds ptxas on the PATH or in /usr/local/cuda.
            library_samples The CUDA toolkits of the externals directory, with the
                            libraries of the samples: cuBLAS, cuFFT, cuRAND, cuSOLVER
                            and cuSPARSE.

        It declares no source code dependencies, as a Triggerable scheduler drives it, but
        checks out the triggering revision to configure the test suite and the GPU libc.

        Property Parameters
        -------------------

        artifact : str
            The name of the toolchain artifact to fetch, which the triggering build sets
            (see getCudaClangBuildFactory). A rebuild keeps it, but the force form cannot
            set it, so instead of forcing this builder, rebuild one of its builds or force
            the triggering builder.

        got_revision : str
            The revision to test, which the triggering build passes through the source
            stamp.

        clean : boolean
            Clean up the source folders. There is no 'clean_obj': every build starts
            from fresh build folders, as the toolchain they were built with is gone.

        jobs : int
            The degree of parallelism of the builds. Used as a default value of the
            'jobs' argument. When the builder does not pass that argument, the worker
            must set this property, or the build fails.

        Worker Info
        -----------

        The files in the info/ directory of the worker which the build reads. Each is
        required unless the builder passes the argument it is the default of.

        artifact_download_command
            The command which downloads the toolchain artifact (see _artifactCommand).
            Used as a default value of the 'download_command' argument.

        gpu_arch
            The GPU architecture of the worker, e.g. "sm_75". Used as a default value of
            the 'gpu_arch' argument.

        test_suite_externals
            The LLVM test suite externals directory of the worker. The CUDA tests get a
            variant per toolkit, C++ standard and standard library in <externals>/cuda,
            so the worker decides what they are tested against. The library samples use
            its cuda-<version> entries as well. Only the stages which use it require it.


        Parameters
        ----------

        test_suite : boolean
            Build and run the CUDA tests of the LLVM test suite (default is False).

        gpu_libc : boolean
            Build and run the GPU libc tests (default is False).

            Note that the GPU libc requires a sm_60 or a newer GPU, so this is not for
            the builders running on the older hardware.

        library_samples : boolean
            Build and run NVIDIA's public samples of its prebuilt CUDA libraries
            (default is False).

        gpu_lock : boolean
            Lock the GPU for the steps running tests on it, for workers whose builds
            share a GPU (default is False).

            - The CUDA tests take the lock exclusively: their assert tests fault the
              GPU on purpose, which can kill the contexts of other processes on it.
            - The GPU libc tests and the library samples share it.
            - The lock is named after the GPU's UUID, so the worker must see exactly
              one GPU. The steps taking the lock fail otherwise.

        gpu_arch : str, optional
            The GPU architecture to compile the tests for, e.g. "sm_75"
            (default is the worker's info/gpu_arch).

        cuda_test_jobs : int, optional
            A degree of parallelism for the tests running on the GPU (default is 4).
            This applies to the CUDA tests of the LLVM test suite and to the library
            samples.

        download_command : list, optional
            The command which downloads the toolchain artifact, given its name as the last
            argument (default is the worker's info/artifact_download_command).

        The rest of the arguments have the same meaning as in getCudaClangBuildFactory.

        Returns
        -------

        Returns the factory object with the prepared build steps.

    """

    assert test_suite or gpu_libc or library_samples, \
        "At least one of the 'test_suite', 'gpu_libc' and 'library_samples' arguments must be specified."

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

    if library_samples:
        f.addSteps(
            _getCudaLibrarySamplesSteps(
                gpu_arch            = gpu_arch,
                cuda_test_jobs      = cuda_test_jobs,
                gpu_lock            = gpu_lock,
                jobs                = jobs,
                dirs                = dirs,
                env                 = env,
            ))

    return f


def _getGpuInfoStep(dirs, env):

    """ Report the GPU we are about to test on, and fail early if there is none. """

    return steps.ShellCommand(
        name            = "gpu-info",
        command         = ["nvidia-smi", "-L"],
        description     = ["GPU information"],
        haltOnFailure   = True,
        env             = dict(env),
        workdir         = dirs.builddir_path,
    )


def _getGpuUuidStep(dirs, env):

    """ Set the 'gpu_uuid' property to the UUID of the GPU, which names the lock on it
        (see _gpuLock). On a worker which sees more than one GPU, the property holds a
        UUID per line, which _gpuLock rejects.
    """

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

    """ Pack the just built toolchain and upload it with the given command (see
        _artifactCommand).

        Returns a list of the steps to finalize the build workflow with.
    """

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

    """ Trigger the builder which tests the just built toolchain.

        Returns a list of the steps to finalize the build workflow with.
    """

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

    """ Replace the toolchain directory with the toolchain of the triggering build,
        discarding the test build directories it has compiled before.

        The artifact gets downloaded with the given command (see _artifactCommand).
    """

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
                                   dirs.libc_obj_dir,
                                   dirs.samples_obj_dir],
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

    """ Check out the latest LLVM test suite, which the CUDA tests come from.

        Its Git step sets got_revision like any other, so it must come before the
        llvm-project checkout of the factory: the reporters and the build page then
        show the revision under test, not the test suite's.
    """

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

    """ Build and run the CUDA tests of the LLVM test suite.

        What they are tested against comes from the externals directory of the worker
        (see the 'test_suite_externals' worker info in getCudaGpuTestFactory).

        Returns the factory object to extend a build workflow with.
    """

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

    """ Build the GPU libc as a stand-alone runtimes build and run its tests on the GPU.

        Note that the factory sets the 'srcdir', 'objdir' and the like properties of the
        build to its own, so the stages after this one must not rely on them.

        Returns a factory to extend a build workflow with.
    """

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


# The CMake project which builds and runs the library samples.
_cuda_library_samples_superbuild = os.path.join(
    os.path.dirname(__file__), "cuda", "library-samples", "CMakeLists.txt")


def _getCudaLibrarySamplesSteps(
        gpu_arch,
        cuda_test_jobs,
        gpu_lock,
        jobs,
        dirs,
        env,
    ):

    """ Build NVIDIA's public samples of its prebuilt CUDA libraries with the unpacked
        Clang and run them on the GPU.

        Returns a list of the steps to extend a build workflow with.
    """

    obj_path = util.Interpolate(f"%(prop:builddir)s/{dirs.samples_obj_dir}")

    return [
        # A shallow fetch of the pinned commit, as the Git step cannot check out a commit
        # of a repository other than the build's.
        steps.ShellSequence(
            name            = "checkout-library-samples",
            commands        = [
                util.ShellArg(
                    command         = ["rm", "-rf", dirs.samples_src_dir],
                    logname         = "stdio",
                    haltOnFailure   = True),
                util.ShellArg(
                    command         = ["git", "init", "--quiet", dirs.samples_src_dir],
                    logname         = "stdio",
                    haltOnFailure   = True),
                util.ShellArg(
                    command         = ["git", "-C", dirs.samples_src_dir, "fetch", "--depth", "1",
                                       _cuda_library_samples_repo, _cuda_library_samples_revision],
                    logname         = "stdio",
                    haltOnFailure   = True),
                util.ShellArg(
                    command         = ["git", "-C", dirs.samples_src_dir, "checkout", "--force", "--detach",
                                       "FETCH_HEAD"],
                    logname         = "stdio",
                    haltOnFailure   = True),
            ],
            description     = ["Checkout the library samples"],
            haltOnFailure   = True,
            env             = dict(env),
            workdir         = dirs.builddir_path,
        ),

        steps.FileDownload(
            mastersrc       = _cuda_library_samples_superbuild,
            name            = "write-library-samples-superbuild",
            workerdest      = f"{dirs.superbuild_dir}/CMakeLists.txt",
            haltOnFailure   = True,
            workdir         = dirs.builddir_path,
        ),

        steps.ShellCommand(
            name            = "cmake-configure-library-samples",
            command         = [
                "cmake", "-G", "Ninja",
                "-S", dirs.superbuild_dir,
                "-B", dirs.samples_obj_dir,
                util.Interpolate(f"-DSAMPLES_DIR=%(prop:builddir)s/{dirs.samples_src_dir}"),
                util.Interpolate("-DTEST_SUITE_EXTERNALS=%(kw:externals)s", externals = dirs.externals_path),
                util.Interpolate("-DCLANG_DIR=%(kw:dir)s", dir = dirs.toolchain_path),
                util.Interpolate("-DGPU_ARCH=%(kw:gpu_arch)s", gpu_arch = gpu_arch),
            ],
            description     = ["Configure the library samples"],
            haltOnFailure   = True,
            env             = dict(env),
            workdir         = dirs.builddir_path,
        ),

        # A sample which fails to build fails its test below, so keep going.
        steps.ShellCommand(
            name            = "build-library-samples",
            command         = ["ninja", "-k", "0", "-j", util.Interpolate("%(kw:jobs)s", jobs = jobs)],
            description     = ["Build the library samples"],
            haltOnFailure   = False,
            env             = dict(env),
            workdir         = obj_path,
        ),

        steps.ShellCommand(
            name            = "test-library-samples",
            command         = ["ctest", "--verbose", "--no-tests=error",
                               "-j", util.Interpolate("%(kw:jobs)s", jobs = cuda_test_jobs)],
            description     = ["Run the library samples"],
            haltOnFailure   = True,
            locks           = _gpuLock.withArgs("counting") if gpu_lock else [],
            env             = dict(env),
            workdir         = obj_path,
        ),
    ]
