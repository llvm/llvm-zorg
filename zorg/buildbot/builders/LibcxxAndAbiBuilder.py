import buildbot.steps.shell
import buildbot.process.properties as properties

from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.process.factory import LLVMBuildFactory
from zorg.buildbot.builders import UnifiedTreeBuilder

def getLibcxxAndAbiBuilder(f=None, env=None,
                           cmake_extra_opts=None, lit_extra_opts=None,
                           lit_extra_args=None, check_libcxx_abilist=False,
                           check_libcxx_benchmarks=None,
                           depends_on_projects=None,
                           use_cache=None,
                           **kwargs):

    if env is None:
        env = {}
    if cmake_extra_opts is None:
        cmake_extra_opts = {}
    if lit_extra_opts is None:
        lit_extra_opts = {}
    if lit_extra_args is None:
        lit_extra_args = []

    if depends_on_projects is None:
        depends_on_projects = ['libcxx','libcxxabi','libunwind']

    src_root = 'llvm'
    build_path = 'build'

    if f is None:
        f = UnifiedTreeBuilder.getLLVMBuildFactoryAndSourcecodeSteps(
                depends_on_projects=depends_on_projects,
                llvm_srcdir=src_root,
                obj_dir=build_path,
                **kwargs) # Pass through all the extra arguments.

    rel_src_dir = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, build_path)

    # Specify the max number of threads using properties so LIT doesn't use
    # all the threads on the system.
    litTestArgs = '-vv --show-unsupported --show-xfail --threads=%(jobs)s'
    if lit_extra_args:
        litTestArgs += ' ' + ' '.join(lit_extra_args)

    for key in lit_extra_opts:
        litTestArgs += (' --param=' + key + '=' + lit_extra_opts[key])

    cmake_opts = [properties.WithProperties('-DLLVM_LIT_ARGS='+litTestArgs)]
    for key in cmake_extra_opts:
        cmake_opts.append('-D' + key + '=' + cmake_extra_opts[key])

    if use_cache:
      libcxx_cache_dir = '%s/../libcxx/cmake/caches' % rel_src_dir
      cache = '%s/%s' % (libcxx_cache_dir, use_cache)
      cmake_opts.append('-C' + cache)

    # FIXME: The libc++ abilist's are generated in release mode with debug
    # symbols Other configurations may contain additional non-inlined symbols.
    if check_libcxx_abilist and not 'CMAKE_BUILD_TYPE' in cmake_extra_opts:
       cmake_opts.append('-DCMAKE_BUILD_TYPE=RELWITHDEBINFO')

    # Force libc++ to use the in-tree libc++abi unless otherwise specified.
    if 'LIBCXX_CXX_ABI' not in cmake_extra_opts:
        cmake_opts.append('-DLIBCXX_CXX_ABI=libcxxabi')

    # Nuke/remake build directory and run CMake
    f.addStep(buildbot.steps.shell.ShellCommand(
        name='rm.builddir', command=['rm', '-rf', build_path],
        workdir=".",
        haltOnFailure=False))

    CmakeCommand.applyRequiredOptions(cmake_opts, [
        ('-DLLVM_ENABLE_PROJECTS=', ";".join(f.depends_on_projects)),
        ])

    f.addStep(buildbot.steps.shell.ShellCommand(
        name='cmake', command=['cmake', rel_src_dir] + cmake_opts,
        haltOnFailure=True, workdir=build_path, env=env))

    # Build libcxxabi
    jobs_flag = properties.WithProperties('-j%(jobs)s')
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='build.libcxxabi', command=['make', jobs_flag, 'cxxabi'],
              haltOnFailure=True, workdir=build_path))

    # Build libcxx
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='build.libcxx', command=['make', jobs_flag, 'cxx'],
              haltOnFailure=True, workdir=build_path))

    # Test libc++abi
    f.addStep(LitTestCommand(
        name            = 'test.libcxxabi',
        command         = ['make', jobs_flag, 'check-cxxabi'],
        description     = ['testing', 'libcxxabi'],
        descriptionDone = ['test', 'libcxxabi'],
        workdir         = build_path))

    # Test libc++
    f.addStep(LitTestCommand(
        name            = 'test.libcxx',
        command         = ['make', jobs_flag, 'check-cxx'],
        description     = ['testing', 'libcxx'],
        descriptionDone = ['test', 'libcxx'],
        workdir         = build_path))

    if check_libcxx_abilist:
        f.addStep(buildbot.steps.shell.ShellCommand(
        name            = 'test.libcxx.abilist',
        command         = ['make', 'check-cxx-abilist'],
        description     = ['testing', 'libcxx', 'abi'],
        descriptionDone = ['test', 'libcxx', 'abi'],
        workdir         = build_path))

    if check_libcxx_benchmarks:
      # Build the libc++ benchmarks
      f.addStep(buildbot.steps.shell.ShellCommand(
          name='build.libcxx.benchmarks',
          command=['make', jobs_flag, 'cxx-benchmarks'],
          haltOnFailure=True, workdir=build_path))

      # Run the benchmarks
      f.addStep(LitTestCommand(
          name            = 'test.libcxx.benchmarks',
          command         = ['make', jobs_flag, 'check-cxx-benchmarks'],
          description     = ['testing', 'libcxx', 'benchmarks'],
          descriptionDone = ['test', 'libcxx', 'benchmarks'],
          workdir         = build_path))

    return f
