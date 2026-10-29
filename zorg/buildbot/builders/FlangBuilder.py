from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.process.factory import LLVMBuildFactory
from zorg.buildbot.builders import TestSuiteBuilder
from zorg.buildbot.builders.UnifiedTreeBuilder import addNinjaSteps, getCmakeWithNinjaBuildFactory
from buildbot.plugins import util, steps
import os

def getFlangOutOfTreeBuildFactory(
           checks = None,
           clean = False,
           run_test_suite = False,
           llvm_extra_configure_args = None,
           flang_extra_configure_args = None,
           flang_rt_extra_configure_args = None,
           test_suite_extra_configure_args = None,
           env = None,
           **kwargs):

    if env is None:
        env = dict()

    # Currently, when Flang is built out-of-tree, it fails to find compiler-rt
    # when linking programs.
    # See https://github.com/llvm/llvm-project/issues/147738.
    # As a workaround, install LLVM, clang, compiler-rt and flang into the same
    # directory and use it to build and test flang-rt.
    install_dir = "install"

    f = getCmakeWithNinjaBuildFactory(
            depends_on_projects=['llvm','clang','mlir','openmp','flang','flang-rt','compiler-rt'],
            enable_projects=['llvm','clang','mlir'],
            enable_runtimes=['openmp','compiler-rt'],
            obj_dir="build_llvm",
            install_dir=install_dir,
            checks=[],
            clean=clean,
            extra_configure_args=llvm_extra_configure_args,
            env=env,
            **kwargs)

    if checks is None:
        checks = ['check-flang', 'check-flang-rt']

    flang_checks = [check for check in checks if check != 'check-flang-rt']
    flang_rt_checks = [check for check in checks if check == 'check-flang-rt']

    cleanBuildRequested = (
        lambda step: step.build.getProperty("clean")
        or step.build.getProperty("clean_obj")
        or clean
    )

    # Make a local copy of the flang configure args, as we are going to modify that.
    if flang_extra_configure_args:
        flang_cmake_args = flang_extra_configure_args[:]
    else:
        flang_cmake_args = list()

    # Some options are required for this build no matter what.
    CmakeCommand.applyRequiredOptions(flang_cmake_args, [
        ('-G', 'Ninja'),
        ])

    flang_obj_dir = "build_flang"
    flang_src_dir = "{}/flang".format(f.monorepo_dir)

    # Add LLVM_DIR and MLIR_DIR to the CMake invocation.
    llvm_dir = "{}/lib/cmake/llvm".format(f.obj_dir)
    mlir_dir = "{}/lib/cmake/mlir".format(f.obj_dir)
    clang_dir = "{}/lib/cmake/clang".format(f.obj_dir)
    CmakeCommand.applyRequiredOptions(flang_cmake_args, [
        ('-DLLVM_DIR:PATH=',
            LLVMBuildFactory.pathRelativeTo(llvm_dir, flang_obj_dir)),
        ('-DMLIR_DIR:PATH=',
            LLVMBuildFactory.pathRelativeTo(mlir_dir, flang_obj_dir)),
        ('-DCLANG_DIR:PATH=',
            LLVMBuildFactory.pathRelativeTo(clang_dir, flang_obj_dir)),
        ('-DCMAKE_INSTALL_PREFIX=',
            LLVMBuildFactory.pathRelativeTo(install_dir, flang_obj_dir)),
        ])

    f.addStep(
        steps.RemoveDirectory(
            name=f"clean-{flang_obj_dir}-dir",
            dir=flang_obj_dir,
            haltOnFailure=False,
            flunkOnFailure=False,
            doStepIf=cleanBuildRequested,
        )
    )

    # We can't use addCmakeSteps as that would use the path in f.llvm_srcdir.
    f.addStep(CmakeCommand(name="cmake-configure-flang",
                           haltOnFailure=True,
                           description=["CMake", "configure", "flang"],
                           options=flang_cmake_args,
                           path=LLVMBuildFactory.pathRelativeTo(flang_src_dir,
                                                                flang_obj_dir),
                           env=env,
                           workdir=flang_obj_dir,
                           **kwargs))

    addNinjaSteps(
       f,
       obj_dir=flang_obj_dir,
       install_dir=install_dir,
       checks=flang_checks,
       env=env,
       stage_name="flang",
       **kwargs)

    ## Build Flang-RT as a standalone runtime
    flang_rt_obj_dir = "build_flang-rt"

    flang_rt_cmake_args = ["-GNinja"]
    if flang_rt_extra_configure_args:
        flang_rt_cmake_args += flang_rt_extra_configure_args

    # Use LLVM from the getCmakeWithNinjaBuildFactory step.
    flang_rt_cmake_args += [
        util.Interpolate(f"-DLLVM_BINARY_DIR=%(prop:builddir)s/{f.obj_dir}"),
        "-DLLVM_ENABLE_RUNTIMES=flang-rt",
    ]

    # Use the Fortran compiler installed in the previous step.
    flang_rt_cmake_args += [
        util.Interpolate(
            f"-DCMAKE_Fortran_COMPILER=%(prop:builddir)s/{install_dir}/bin/flang"
        ),
        "-DCMAKE_Fortran_COMPILER_WORKS=ON",
    ]

    f.addStep(
        steps.RemoveDirectory(
            name=f"clean-{flang_rt_obj_dir}-dir",
            dir=flang_rt_obj_dir,
            haltOnFailure=False,
            flunkOnFailure=False,
            doStepIf=cleanBuildRequested,
        )
    )

    f.addStep(
        CmakeCommand(
            name="cmake-configure-flang-rt",
            haltOnFailure=True,
            description=["CMake", "configure", "Flang-RT"],
            options=flang_rt_cmake_args,
            path=LLVMBuildFactory.pathRelativeTo(
                os.path.join(f.monorepo_dir, "runtimes"), flang_rt_obj_dir
            ),
            env=env,
            workdir=flang_rt_obj_dir,
            **kwargs,
        )
    )

    addNinjaSteps(
       f,
       obj_dir=flang_rt_obj_dir,
       install_dir=install_dir,
       checks=flang_rt_checks,
       env=env,
       stage_name="flang-rt",
       **kwargs)

    if run_test_suite:
        test_suite_obj_dir = "build_llvm-test-suite"
        test_suite_cmake_definitions = {
            "CMAKE_BUILD_TYPE": "Release",
            "CMAKE_C_COMPILER": util.Interpolate(
                f"%(prop:builddir)s/{install_dir}/bin/clang"
            ),
            "CMAKE_CXX_COMPILER": util.Interpolate(
                f"%(prop:builddir)s/{install_dir}/bin/clang++"
            ),
            "CMAKE_Fortran_COMPILER": util.Interpolate(
                f"%(prop:builddir)s/{install_dir}/bin/flang"
            ),
            "TEST_SUITE_COLLECT_CODE_SIZE": "OFF",
            "TEST_SUITE_FORTRAN": "ON",
            "TEST_SUITE_LIT:FILEPATH": util.Interpolate(
                f"%(prop:builddir)s/{f.obj_dir}/bin/llvm-lit"
            ),
            "TEST_SUITE_SUBDIRS": "Fortran",
        }
        if test_suite_extra_configure_args:
            test_suite_cmake_definitions.update(test_suite_extra_configure_args)

        f.addStep(
            steps.RemoveDirectory(
                name=f"clean-{test_suite_obj_dir}-dir",
                dir=test_suite_obj_dir,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=cleanBuildRequested,
            )
        )

        factory_hint = f.hint
        test_suite_hint = (
            f"{factory_hint}-test-suite" if factory_hint else "test-suite"
        )
        try:
            # getLlvmTestSuiteSteps uses the factory hint for checkout and
            # configure step names. Give its nested steps unique names.
            f.hint = test_suite_hint
            TestSuiteBuilder.getLlvmTestSuiteSteps(
                cmake_definitions=test_suite_cmake_definitions,
                targets=["."],
                checks=["check"],
                env=env,
                hint=test_suite_hint,
                obj_dir=test_suite_obj_dir,
                f=f,
            )
        finally:
            f.hint = factory_hint

    return f
