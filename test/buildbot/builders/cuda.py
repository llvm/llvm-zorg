# RUN: python %s

# Lit Regression Tests for the CudaBuilder factories.

import os

from buildbot.plugins import util
from buildbot.process.properties import Properties
from buildbot.steps.source.git import Git
from twisted.python.failure import Failure

import zorg
from zorg.buildbot.builders import CudaBuilder

from zorg.buildbot.tests import factory_has_step, partly_rendered

GPU_TRIPLE = "nvptx64-nvidia-cuda"


# The build factory. Use all defaults.
f = CudaBuilder.getCudaClangBuildFactory()
print(f"default build factory: {f}\n")

# The projects it builds, which decide the commits it gets scheduled for.
assert sorted(f.depends_on_projects) == sorted([
    "clang", "libc", "libcxx", "libcxxabi", "libunwind", "llvm", "offload", "openmp",
])

# Without publishing there is nothing to publish or trigger, and so no upload command
# for the worker to provide.
assert not factory_has_step(f, "publish-artifact")
assert not factory_has_step(f, "trigger-gpu-tests")

# The build half of the two-builder configuration.
f = CudaBuilder.getCudaClangBuildFactory(publish_artifact = True, trigger_scheduler = "gpu-tests")
print(f"publishing build factory: {f}\n")

assert factory_has_step(f, "set-props-artifact")
assert factory_has_step(f, "cmake-configure", hasarg = "definitions", contains = {
    "LLVM_INSTALL_UTILS"                            : "ON",
    "LLVM_RUNTIME_TARGETS"                          : f"default;{GPU_TRIPLE}",
    f"RUNTIMES_{GPU_TRIPLE}_LLVM_ENABLE_RUNTIMES"   : "libc",
})
# The artifact is the install, so a previous one must not ship with it.
assert factory_has_step(f, "remove-previous-install")
assert factory_has_step(f, "publish-artifact")
# The GPU builders get the name of the artifact of this build.
assert factory_has_step(f, "trigger-gpu-tests", hasarg = "set_properties", contains = {
    "artifact" : util.Property("artifact"),
})

# Triggering the test builders with no artifact for them to test is an error.
try:
    CudaBuilder.getCudaClangBuildFactory(trigger_scheduler = "gpu-tests")
    assert False, "a trigger without publishing was accepted"
except AssertionError as e:
    assert "publish_artifact" in str(e)


# The GPU test factory, with all of its stages.
all_stages = {"test_suite" : True, "gpu_libc" : True, "library_samples" : True}
f = CudaBuilder.getCudaGpuTestFactory(**all_stages, gpu_arch = "sm_75")
print(f"GPU test factory: {f}\n")

# A GPU test factory which tests nothing is an error.
try:
    CudaBuilder.getCudaGpuTestFactory()
    assert False, "a GPU test factory without stages was accepted"
except AssertionError as e:
    assert "At least one of" in str(e)

# A Triggerable scheduler drives it, so it must declare no source code dependencies:
# otherwise the commits to the LLVM projects would also schedule it (see
# getMainBranchSchedulers).
assert not f.depends_on_projects

# The llvm-project checkout comes last, so that got_revision is the revision under test
# rather than the test suite's.
names = [partly_rendered(s.kwargs.get("name")) for s in f.steps]
assert names.index("checkout-cuda-test-suite") < names.index("checkout")
assert not any(issubclass(s.step_class, Git) for s in f.steps[names.index("checkout") + 1:])

assert factory_has_step(f, "fetch-artifact")
# Otherwise libc builds no tests at all, and check-libc passes.
assert factory_has_step(f, "cmake-configure-nvptx-libc", hasarg = "definitions", contains = {
    "LIBC_GPU_TEST_ARCHITECTURE" : "sm_75",
})
# The superbuild of the library samples is a file sent from the master.
# Some step names are renderables, which compare as a renderable rather than a boolean.
superbuild = [s for s in f.steps
              if isinstance(s.kwargs.get("name"), str) and s.kwargs["name"] == "write-library-samples-superbuild"]
assert len(superbuild) == 1
assert os.path.isfile(superbuild[0].kwargs["mastersrc"])
# The tests which need the GPU to themselves run in a step of their own, the rest in
# another: both select them by the label the superbuild gives them.
def step_command(name):
    return " ".join(str(a) for s in f.steps if partly_rendered(s.kwargs.get("name")) == name
                    for a in s.kwargs["command"])

assert " -LE exclusive_gpu " in step_command("test-library-samples")
assert " -L exclusive_gpu" in step_command("test-library-samples-exclusive-gpu")
assert "LABELS exclusive_gpu RUN_SERIAL TRUE" in open(superbuild[0].kwargs["mastersrc"]).read()

# Each stage adds its own steps, and only those.
stages = {
    "test_suite"        : "cmake-configure-cuda-test-suite",
    "gpu_libc"          : "cmake-configure-nvptx-libc",
    "library_samples"   : "cmake-configure-library-samples",
}
for stage in stages:
    f = CudaBuilder.getCudaGpuTestFactory(**{s : s == stage for s in stages})
    print(f"GPU test factory with only {stage}: {f}\n")
    assert factory_has_step(f, "fetch-artifact")
    for other, step in stages.items():
        assert factory_has_step(f, step) == (other == stage)


# The renderers which read what the worker provides.
class FakeBuild:
    def __init__(self, info):
        self.info = Properties(**info)

    def getWorkerInfo(self):
        return self.info


def render(renderable, info = None, **properties):
    props = Properties(**properties)
    props.build = FakeBuild(info or {})
    results = []
    props.render(renderable).addBoth(results.append)
    return results[0]


def fails_with(result, message):
    return isinstance(result, Failure) and message in str(result.value)


# Worker info comes from files, so their trailing newline is not part of the value.
assert render(CudaBuilder._requiredWorkerInfo.withArgs("gpu_arch"), {"gpu_arch" : "sm_86\n"}) == "sm_86"
assert fails_with(render(CudaBuilder._requiredWorkerInfo.withArgs("gpu_arch")),
                  "the worker's info/gpu_arch is not set")
assert fails_with(render(CudaBuilder._requiredProperty.withArgs("jobs")), "the 'jobs' property is not set")

# An artifact command is a string to split, or a list, followed by the artifact.
assert render(CudaBuilder._artifactCommand.withArgs("artifact-store put"),
              artifact = "clang-cuda-r-b1.tar") == ["artifact-store", "put", "clang-cuda-r-b1.tar"]
assert render(CudaBuilder._artifactCommand.withArgs(["up", "--to", "a b"]),
              artifact = "clang-cuda-r-b1.tar") == ["up", "--to", "a b", "clang-cuda-r-b1.tar"]


# Without 'gpu_lock', there is no lock on the GPU, and no UUID to name it after.
f = CudaBuilder.getCudaGpuTestFactory(**all_stages, gpu_arch = "sm_75")
assert not factory_has_step(f, "set-props-gpu-uuid")
assert all(not s.kwargs.get("locks") for s in f.steps)

# With it, the lock on the GPU is named after the UUID the build reads from the worker
# before any step takes the lock.
f = CudaBuilder.getCudaGpuTestFactory(**all_stages, gpu_lock = True, gpu_arch = "sm_75")
names = [partly_rendered(s.kwargs.get("name")) for s in f.steps]
assert names.index("gpu-info") < names.index("set-props-gpu-uuid") < names.index("fetch-artifact")
assert factory_has_step(f, "set-props-gpu-uuid", hasarg = "property", contains = "gpu_uuid")

# The CUDA tests take it exclusively, as their assert tests fault the GPU, and so do
# the cuFFT multi-GPU samples, which go wrong on a shared GPU. The other tests on the
# GPU share it. No other step takes it.
gpu_lock_modes = {
    "test-check-cuda-simple-cuda-test-suite"    : "exclusive",
    "test-check-libc-nvptx-libc"                : "counting",
    "test-library-samples"                      : "counting",
    "test-library-samples-exclusive-gpu"        : "exclusive",
}
for s in f.steps:
    name = partly_rendered(s.kwargs.get("name"))
    if name not in gpu_lock_modes:
        assert not s.kwargs.get("locks"), f"step '{name}' takes a lock"
        continue
    accesses = render(s.kwargs["locks"], gpu_uuid = "GPU-1234")
    assert len(accesses) == 1, f"step '{name}' takes {len(accesses)} locks"
    assert accesses[0].lockid == util.MasterLock("gpu-GPU-1234", maxCount = CudaBuilder._gpu_lock_max_count)
    assert accesses[0].mode == gpu_lock_modes[name], f"step '{name}' takes the lock {accesses[0].mode}"
assert all(name in names for name in gpu_lock_modes)

assert fails_with(render(CudaBuilder._gpuLock.withArgs("counting")), "the 'gpu_uuid' property is not set")
# A worker which sees several GPUs gets a UUID per line, and no lock would name the GPU
# the tests run on.
assert fails_with(render(CudaBuilder._gpuLock.withArgs("counting"), gpu_uuid = "GPU-1234\nGPU-5678"),
                  "the worker sees 2 GPUs (GPU-1234, GPU-5678) rather than one")
