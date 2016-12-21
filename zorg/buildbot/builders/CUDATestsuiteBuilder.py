from buildbot.process.properties import WithProperties
try:
  # buildbot 0.8.5
  from buildbot.steps.slave import RemoveDirectory
except:
  # buildbot 0.8.12
  from buildbot.plugins import steps
  RemoveDirectory = steps.RemoveDirectory

from zorg.buildbot.builders import ClangBuilder
from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand


def getCUDATestsuiteBuildFactory(
        externals,  # Directory with CUDA, thrust and gcc versions for testing.
        always_clean=True,
        test=False,
        useTwoStage=False,
        cmake='cmake',
        extra_cmake_args=None,  # Extra CMake args for all stages.
        extra_ts_cmake_args=None,  # extra cmake args for testsuite.
        jobs=None,
        cuda_jobs=1,  # number of simultaneous CUDA apps to run
        env=None,  # Environmental variables for all steps.
        enable_thrust_tests=False,
        split_thrust_tests=False,  # Each thrust test is a separate executable.
        run_thrust_tests=False,
        enable_libcxx=True,  # checkout/build libcxx to test with.
        gpu_arch_list=None,
        gpu_devices=None,  # List of devices to make visible to  CUDA
        stage1_config='Release',
        stage2_config='Release'):

    if extra_cmake_args is None:
        extra_cmake_args = []
    if extra_ts_cmake_args is None:
        extra_ts_cmake_args = []

    # Prepare environmental variables. Set here all env we want for all steps.
    merged_env = {
        'TERM': 'dumb'  # Make sure Clang doesn't use color escape sequences.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set
        # anything.
        merged_env.update(env)

    source_dir = 'llvm'   # Should match the one used in getClangCMakeBuildFactory.
    stage1_build_dir = 'stage1'  # Should match the one defined in getClangCMakeBuildFactory.
    stage2_build_dir = 'stage2'  # Should match the one defined in getClangCMakeBuildFactory.

    if useTwoStage:
        clang_build_dir = stage2_build_dir
    else:
        clang_build_dir = stage1_build_dir

    # Build clang.
    f = ClangBuilder.getClangCMakeBuildFactory(
            clean=always_clean,
            test=test,
            cmake=cmake,
            extra_cmake_args=extra_cmake_args,
            jobs=jobs,
            env=merged_env,
            useTwoStage=useTwoStage,
            stage1_config=stage1_config,
            stage2_config=stage2_config,
            checkout_libcxx=enable_libcxx,
            checkout_test_suite=True)

    cuda_test_env = {
        'PYTHONPATH': WithProperties("%(workdir)s/" + source_dir +
                                     "/utils/lit:${PYTHONPATH}"),
        'PATH': WithProperties("%(workdir)s/" + clang_build_dir +
                               "/bin:${PATH}"),
    }
    # Limit GPUs visible to CUDA.
    if gpu_devices:
        cuda_test_env["CUDA_VISIBLE_DEVICES"] = ",".join(
            str(x) for x in gpu_devices)
    merged_env.update(cuda_test_env)

    ts_build_dir = 'test-suite-build'

    # Completely remove test suite build dir.
    f.addStep(
        RemoveDirectory(name="Remove old test-suite build directory",
                        dir=ts_build_dir))

    if extra_ts_cmake_args:
        cmake_args = extra_ts_cmake_args[:]
    else:
        cmake_args = []

    # Set proper defaults.
    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-DCMAKE_BUILD_TYPE=',        'Release'),
    ])

    # Some options are required for this stage no matter what.
    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-G',                      'Ninja'),
    ])

    cmake_args.append(
        WithProperties(
            "-DCMAKE_CXX_COMPILER=%(workdir)s/" +
                                    clang_build_dir + "/bin/clang++"
        ))
    cmake_args.append(
        WithProperties(
            "-DCMAKE_C_COMPILER=%(workdir)s/" + clang_build_dir + "/bin/clang"
        ))

    cmake_args.append('-DTEST_SUITE_SUBDIRS=External'),
                      # Limit to External tests only.

    if externals:
        cmake_args.append('-DTEST_SUITE_EXTERNALS_DIR=' + externals)
    if split_thrust_tests:
        cmake_args.append('-DTHRUST_SPLIT_TESTS=1')
    if gpu_arch_list:
        cmake_args.append('-DCUDA_GPU_ARCH=' + ';'.join(gpu_arch_list))
    if cuda_jobs:
        cmake_args.append('-DCUDA_JOBS=%s' % cuda_jobs)

    # Then do fresh cmake configuration.
    f.addStep(CmakeCommand(name='cmake test-suite',
                           description='cmake test-suite',
                           haltOnFailure=True,
                           options=cmake_args,
                           path="../test/test-suite",
                           workdir=ts_build_dir,
                           env=merged_env))

    # Always build simple CUDA tests. They serve as compilation
    # smoketests and will fail quickly if compiler has obvious issues
    # compiling CUDA files.
    f.addStep(NinjaCommand(
        name='ninja build simple CUDA tests',
        targets=["cuda-tests-simple"],
        jobs=jobs,
        haltOnFailure=True,
        description=["building simple CUDA tests"],
        descriptionDone=["simple CUDA tests built."],
        workdir=ts_build_dir,
        env=merged_env))

    f.addStep(NinjaCommand(
        name='run simple CUDA tests',
        targets=["check-cuda-simple"],
        jobs=1, # lit will parallelize the jobs
        haltOnFailure=True,
        description=["Running simple CUDA tests"],
        descriptionDone=["simple CUDA tests done."],
        workdir=ts_build_dir,
        env=merged_env))

    # If we've enabled thrust tests, build them now.
    # WARNING: This takes a lot of time to build.
    if (enable_thrust_tests):
        f.addStep(NinjaCommand(
            name='ninja build thrust',
            targets=["cuda-tests-thrust"],
            jobs=jobs,
            haltOnFailure=True,
            description=["building thrust tests"],
            descriptionDone=["thrust tests built."],
            workdir=ts_build_dir,
            env=merged_env))
        # Run them. That also takes a while.
        # TODO(tra) we may want to run more than one instance so one
        # can be compiling tests while another is running them on GPU.
        if run_thrust_tests:
            f.addStep(NinjaCommand(
                name='run all CUDA tests',
                targets=["check"],
                jobs=1, # lit will parallelize the jobs.
                haltOnFailure=True,
                description=["running all CUDA tests."],
                descriptionDone=["all cuda tests done."],
                workdir=ts_build_dir,
                env=merged_env))

    return f
