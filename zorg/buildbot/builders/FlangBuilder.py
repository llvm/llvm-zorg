from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.process.factory import LLVMBuildFactory
from zorg.buildbot.builders.UnifiedTreeBuilder import addNinjaSteps, getCmakeWithNinjaBuildFactory
from buildbot.plugins import util, steps
import os

def getFlangOutOfTreeBuildFactory(
           checks = None,
           clean = False,
           llvm_extra_configure_args = None,
           flang_extra_configure_args = None,
           flang_rt_extra_configure_args = None,
           env = None,
           **kwargs):

    if env is None:
        env = dict()

    f = getCmakeWithNinjaBuildFactory(
            depends_on_projects=['llvm','clang','mlir','openmp','flang','flang-rt'],
            enable_projects=['llvm','clang','mlir'],
            enable_runtimes=['openmp', 'compiler-rt'],
            obj_dir="build_llvm",
            checks=[],
            clean=clean,
            extra_configure_args=llvm_extra_configure_args,
            env=env,
            **kwargs)

    if checks is None:
        checks = ['check-all']

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
       checks=checks,
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

    # Use the Fortran compiler from the previous step.
    flang_rt_cmake_args += [
        util.Interpolate(
            f"-DCMAKE_Fortran_COMPILER=%(prop:builddir)s/{flang_obj_dir}/bin/flang"
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
       checks=['check-flang-rt'],
       env=env,
       stage_name="flang-rt",
       **kwargs)

    return f
