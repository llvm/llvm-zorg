from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.process.factory import LLVMBuildFactory
from zorg.buildbot.builders.UnifiedTreeBuilder import addNinjaSteps, getCmakeWithNinjaBuildFactory

def getFlangOutOfTreeBuildFactory(
           checks = None,
           clean = False,
           llvm_extra_configure_args = None,
           flang_extra_configure_args = None,
           env = None,
           **kwargs):

    if env is None:
        env = dict()

    f = getCmakeWithNinjaBuildFactory(
            depends_on_projects=['llvm','clang','mlir','openmp'],
            obj_dir="build_llvm",
            checks=[],
            clean=clean,
            extra_configure_args=llvm_extra_configure_args,
            env=env,
            **kwargs)

    if checks is None:
        checks = ['check-all']

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
        # We actually need the paths to be relative to the source directory,
        # otherwise find_package can't locate the config files.
        ('-DLLVM_DIR:PATH=',
            LLVMBuildFactory.pathRelativeTo(llvm_dir, flang_src_dir)),
        ('-DMLIR_DIR:PATH=',
            LLVMBuildFactory.pathRelativeTo(mlir_dir, flang_src_dir)),
        ('-DCLANG_DIR:PATH=',
            LLVMBuildFactory.pathRelativeTo(clang_dir, flang_src_dir)),
        ])

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

    return f
