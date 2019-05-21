from buildbot.steps.shell import ShellCommand
from buildbot.steps.slave import RemoveDirectory
from buildbot.status.results import FAILURE
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand
from zorg.buildbot.conditions.FileConditions import FileDoesNotExist
from zorg.buildbot.process.factory import LLVMBuildFactory

def _addSteps4SystemCompiler(
           f,
           stage_idx = 0,
           clean = True,
           jobs  = None,
           extra_configure_args = None,
           env   = None):

    # Index is zero-based, so we want to use a human friendly  number instead.
    stage_num = stage_idx + 1

    # Directories to use on this stage.
    obj_dir = f.stage_objdirs[stage_idx]
    src_dir = LLVMBuildFactory.pathRelativeToBuild(f.llvm_srcdir, obj_dir)
    install_dir = LLVMBuildFactory.pathRelativeToBuild(f.stage_installdirs[stage_idx], obj_dir)

    # This stage could use incremental build.
    # Clean stage1, only if requested.
    f.addStep(RemoveDirectory(name='clean-%s-dir' % obj_dir,
              dir=obj_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=clean
              ))
    f.addStep(RemoveDirectory(name='clean-%s-dir' % f.stage_installdirs[stage_idx],
              dir=f.stage_installdirs[stage_idx],
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=clean
              ))

    # Reconcile the cmake options for this stage.

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    # Set proper defaults.
    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-DCMAKE_BUILD_TYPE=',        'Release'),
        ('-DCLANG_BUILD_EXAMPLES=',    'OFF'),
        ('-DLLVM_BUILD_TESTS=',        'ON'),
        ('-DLLVM_ENABLE_ASSERTIONS=',  'OFF'),
        ('-DLLVM_OPTIMIZED_TABLEGEN=', 'ON'),
        # Do not expect warning free build by the system toolchain.
        ('-DLLVM_ENABLE_WERROR=',      'OFF'),
        ])

    # Some options are required for this stage no matter what.
    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-G',                      'Ninja'),
        ('-DCMAKE_INSTALL_PREFIX=', install_dir),
        ])

    # Note: On this stage we do not care of warnings, as we build with
    # a system toolchain and cannot control the environment.
    # Warnings are likely, and we ignore them.

    # Create configuration files with cmake
    f.addStep(CmakeCommand(name="cmake-configure-stage%s" % stage_num,
                           description=["stage%s cmake configure" % stage_num],
                           haltOnFailure=True,
                           flunkOnWarnings=False,
                           options=cmake_args,
                           path=src_dir,
                           env=env,
                           workdir=obj_dir,
                           doStepIf=FileDoesNotExist("CMakeCache.txt")
                           ))

    # Build clang by the system compiler
    f.addStep(NinjaCommand(name="build-stage%s-compiler" % stage_num,
                           jobs=jobs,
                           haltOnFailure=True,
                           flunkOnWarnings=False,
                           description=["build stage%s compiler" % stage_num],
                           env=env,
                           workdir=obj_dir,
                           ))

    # Test stage1 compiler
    f.addStep(NinjaCommand(name="test-stage%s-compiler"% stage_num,
                           targets=["check-all"], # or "check-llvm", "check-clang"
                           jobs=jobs,
                           haltOnFailure=True,
                           flunkOnWarnings=False,
                           description=["test stage%s compiler" % stage_num],
                           env=env,
                           workdir=obj_dir,
                           ))

    # Install stage1 compiler
    f.addStep(NinjaCommand(name="install-stage%s-compiler"% stage_num,
                           targets=["install"],
                           jobs=jobs,
                           haltOnFailure=True,
                           description=["install stage%s compiler" % stage_num],
                           env=env,
                           workdir=obj_dir,
                           ))


def _addSteps4StagedCompiler(
           f,
           stage_idx = 1,
           use_stage_idx = -1,
           jobs = None,
           extra_configure_args = None,
           env = None):

    if use_stage_idx < 0:
        use_stage_idx = stage_idx - 1

    # Index is zero-based, so we want to use a human friendly  number instead.
    stage_num = stage_idx + 1

    # Directories to use on this stage.
    obj_dir = f.stage_objdirs[stage_idx]
    src_dir = LLVMBuildFactory.pathRelativeToBuild(f.llvm_srcdir, obj_dir)
    install_dir = LLVMBuildFactory.pathRelativeToBuild(f.stage_installdirs[stage_idx], obj_dir)
    staged_install = f.stage_installdirs[use_stage_idx]

    # Always do a clean build for the staged compiler.
    f.addStep(RemoveDirectory(name='clean-%s-dir' % obj_dir,
              dir=obj_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              ))

    f.addStep(RemoveDirectory(name='clean-%s-dir' % f.stage_installdirs[stage_idx],
              dir=f.stage_installdirs[stage_idx],
              haltOnFailure=False,
              flunkOnFailure=False,
              ))

    # Reconcile the cmake options for this stage.

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    # Set proper defaults.
    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-DCMAKE_BUILD_TYPE=',        'Release'),
        ('-DCLANG_BUILD_EXAMPLES=',    'OFF'),
        ('-DLLVM_BUILD_TESTS=',        'ON'),
        ('-DLLVM_ENABLE_ASSERTIONS=',  'ON'),
        ('-DLLVM_OPTIMIZED_TABLEGEN=', 'ON'),
        ])

    # Some options are required for this stage no matter what.
    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-G',                      'Ninja'),
        ('-DCMAKE_INSTALL_PREFIX=', install_dir),
        ])

    cmake_args.append(
        WithProperties(
            "-DCMAKE_CXX_COMPILER=%(workdir)s/" + staged_install + "/bin/clang++"
        ))
    cmake_args.append(
        WithProperties(
            "-DCMAKE_C_COMPILER=%(workdir)s/" + staged_install + "/bin/clang"
        ))

    # Create configuration files with cmake
    f.addStep(CmakeCommand(name="cmake-configure-stage%s" % stage_num,
                           description=["stage%s cmake configure" % stage_num],
                           haltOnFailure=True,
                           options=cmake_args,
                           path=src_dir,
                           env=env,
                           workdir=obj_dir,
                           doStepIf=FileDoesNotExist("CMakeCache.txt")
                           ))

    # Build clang by the staged compiler
    f.addStep(NinjaCommand(name="build-stage%s-compiler" % stage_num,
                           jobs=jobs,
                           haltOnFailure=True,
                           description=["build stage%s compiler" % stage_num],
                           timeout=10800, # LTO could take time.
                           env=env,
                           workdir=obj_dir,
                           ))

    # Test just built compiler
    f.addStep(NinjaCommand(name="test-stage%s-compiler"% stage_num,
                           targets=["check-all"],
                           jobs=jobs,
                           haltOnFailure=True,
                           description=["test stage%s compiler" % stage_num],
                           timeout=10800, # LTO could take time.
                           env=env,
                           workdir=obj_dir,
                           ))

    # Install just built compiler
    f.addStep(NinjaCommand(name="install-stage%s-compiler"% stage_num,
                           targets=["install"],
                           jobs=jobs,
                           haltOnFailure=True,
                           description=["install stage%s compiler" % stage_num],
                           timeout=10800, # LTO could take time.
                           env=env,
                           workdir=obj_dir,
                           ))


def getClangWithLTOBuildFactory(
           depends_on_projects = None,
           clean = False,
           jobs  = None,
           extra_configure_args = None,
           compare_last_2_stages = True,
           lto = None, # The string gets passed to -flto flag as is. Like -flto=thin.
           env = None):

    # Set defaults
    if depends_on_projects:
        depends_on_projects = list(depends_on_projects)
    else:
        # By default we link with LLD.
        depends_on_projects = ['llvm', 'clang', 'lld']

    if lto is None:
        lto = 'ON'

    if jobs is None:
        jobs = "%(jobs)s"

    if extra_configure_args is None:
        extra_configure_args = []
    else:
        extra_configure_args = list(extra_configure_args)

    # Make sure CMAKE_INSTALL_PREFIX and -G are not specified
    # in the extra_configure_args. We set them internally as needed.
    # TODO: assert extra_configure_args.
    install_prefix_specified = any(a.startswith('-DCMAKE_INSTALL_PREFIX=') for a in extra_configure_args)
    assert not install_prefix_specified, "Please do not explicitly specify the install prefix for multi-stage build."

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Be cautious and disable color output from all tools.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    f = LLVMBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir="llvm.src",
            stage_objdirs=[
                "build/stage1",
                "build/stage2",
                "build/stage3",
                "build/stage4",
                ],
            stage_installdirs=[
                "install/stage1",
                "install/stage2",
                "install/stage3",
                "install/stage4",
                ],
            staged_compiler_idx = 1)

    cleanBuildRequested = lambda step: step.build.getProperty("clean") or clean

    # Do a clean checkout if requested.
    f.addStep(RemoveDirectory(name='clean-src-dir',
              dir=f.llvm_srcdir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested,
              ))

    # Get the source code.
    f.addSVNSteps()

    # Build with the system compiler first
    _addSteps4SystemCompiler(f,
                             stage_idx=0,
                             clean=cleanBuildRequested,
                             jobs=jobs,
                             extra_configure_args=extra_configure_args,
                             env=merged_env)

    # Then build the compiler we would use for the bootstrap.
    _addSteps4StagedCompiler(f,
                             stage_idx=1,
                             jobs=jobs,
                             extra_configure_args=extra_configure_args,
                             env=merged_env)

    # Build all the remaining stages with exactly the same configuration.

    CmakeCommand.applyRequiredOptions(extra_configure_args, [
        ('-DLLVM_ENABLE_LTO=', lto),
        ])

    # If we build LLD, we would link with LLD.
    # Otherwise we link with the system linker.
    if 'lld' in depends_on_projects:
        CmakeCommand.applyRequiredOptions(extra_configure_args, [
            ('-DLLVM_ENABLE_LLD=', 'ON'),
            ])

    # The rest are test stages, which depend on the staged compiler we are ultimately after.
    s = f.staged_compiler_idx + 1
    staged_install = f.stage_installdirs[f.staged_compiler_idx]
    for i in range(s, len(f.stage_objdirs[s:]) + s):
        configure_args = extra_configure_args[:]

        configure_args.append(
            WithProperties(
                "-DCMAKE_AR=%(workdir)s/" + staged_install + "/bin/llvm-ar"
            ))
        configure_args.append(
            WithProperties(
                "-DCMAKE_RANLIB=%(workdir)s/" + staged_install + "/bin/llvm-ranlib"
            ))

        _addSteps4StagedCompiler(f,
                                 stage_idx=i,
                                 use_stage_idx=f.staged_compiler_idx,
                                 jobs=jobs,
                                 extra_configure_args=configure_args,
                                 env=merged_env)

    if compare_last_2_stages:
        # Compare the compilers built on the last 2 stages if requested.
        diff_command = [
            "diff",
            "-q",
            f.stage_installdirs[-2] + "/bin/clang",
            f.stage_installdirs[-1] + "/bin/clang",
        ]
        f.addStep(
            ShellCommand(
                name="compare-compilers",
                description=[
                    "compare",
                    "stage%d" % (len(f.stage_installdirs)-1),
                    "and",
                    "stage%d" % len(f.stage_installdirs),
                    "compilers",
                    ],
                haltOnFailure=False,
                command=WithProperties(" ".join(diff_command)),
                workdir=".",
                env=merged_env
            )
        )

        # Only if the compare-compilers step has failed.
        def _prevStepFailed(step):
            steps = step.build.getStatus().getSteps()
            prev_step = steps[-2]
            (result, _) = prev_step.getResults()
            return (result == FAILURE)

        dir1 = f.stage_objdirs[-2]
        dir2 = f.stage_objdirs[-1]
        inc_pattern = "-type f -not -name *.inc -printf '%f\n'"
        find_cmd = "find %s %s" % (dir1, dir2)
        diff_cmd = "diff -ru %s %s -x '*.tmp*' -X -" % (dir1, dir2)

        # Note: Use a string here as we want the command executed by a shell.
        diff_tablegen_inc_files_command = "%s %s | %s" % (find_cmd, inc_pattern, diff_cmd)

        f.addStep(
            ShellCommand(
                name="compare-tablegen-inc-files",
                description=[
                    "compare",
                    "stage%d" % (len(f.stage_installdirs)-1),
                    "and",
                    "stage%d" % len(f.stage_installdirs),
                    "Tablegen inc files",
                    ],
                command=diff_tablegen_inc_files_command,
                workdir=".",
                env=merged_env,
                doStepIf=_prevStepFailed,
            )
        )

    return f
