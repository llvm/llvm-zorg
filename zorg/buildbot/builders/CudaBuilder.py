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

import shlex

from buildbot.plugins import steps, util

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

    """ The directory layout of the CUDA factories. The '*_path' attributes are
        renderables, resolved against the build directory when the build runs.
    """

    def __init__(self):
        self.obj_dir            = "build"
        self.install_dir        = "install"

        self.builddir_path      = util.Interpolate("%(prop:builddir)s")


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
