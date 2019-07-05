import os

import buildbot
import buildbot.process.factory
import buildbot.steps.shell
import buildbot.process.properties as properties

from buildbot.steps.source.svn import SVN

import zorg.buildbot.commands.LitTestCommand as lit_test_command
import zorg.buildbot.util.artifacts as artifacts
import zorg.buildbot.util.phasedbuilderutils as phased_builder_utils

from zorg.buildbot.commands.LitTestCommand import LitTestCommand

reload(lit_test_command)
reload(artifacts)
reload(phased_builder_utils)


def getLibcxxWholeTree(f, src_root):
    llvm_path = src_root
    libcxx_path = properties.WithProperties(
        '%(builddir)s/llvm/projects/libcxx')
    libcxxabi_path = properties.WithProperties(
        '%(builddir)s/llvm/projects/libcxxabi')
    libunwind_path = properties.WithProperties(
        '%(builddir)s/llvm/projects/libunwind')

    f = phased_builder_utils.SVNCleanupStep(f, llvm_path)
    f.addStep(SVN(name='svn-llvm',
                  mode='full',
                  baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvm_path))
    f.addStep(SVN(name='svn-libcxx',
                  mode='full',
                  baseURL='http://llvm.org/svn/llvm-project/libcxx/',
                  defaultBranch='trunk',
                  workdir=libcxx_path))
    f.addStep(SVN(name='svn-libcxxabi',
                  mode='full',
                  baseURL='http://llvm.org/svn/llvm-project/libcxxabi/',
                  defaultBranch='trunk',
                  workdir=libcxxabi_path))
    f.addStep(SVN(name='svn-libunwind',
                  mode='full',
                  baseURL='http://llvm.org/svn/llvm-project/libunwind/',
                  defaultBranch='trunk',
                  workdir=libunwind_path))

    return f


def getLibcxxAndAbiBuilder(f=None, env={}, additional_features=set(),
                           cmake_extra_opts={}, lit_extra_opts={},
                           lit_extra_args=[], check_libcxx_abilist=False,
                           check_libcxx_benchmarks=False):
    if f is None:
        f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(
        name="get_builddir",
        command=["pwd"],
        property="builddir",
        description="set build dir",
        workdir="."))

    src_root = properties.WithProperties('%(builddir)s/llvm')
    build_path = properties.WithProperties('%(builddir)s/build')

    f = getLibcxxWholeTree(f, src_root)

    # Specify the max number of threads using properties so LIT doesn't use
    # all the threads on the system.
    litTestArgs = '-sv --show-unsupported --show-xfail --threads=%(jobs)s'
    if lit_extra_args:
        litTestArgs += ' ' + ' '.join(lit_extra_args)

    if additional_features:
        litTestArgs += (' --param=additional_features=' +
                       ','.join(additional_features))

    for key in lit_extra_opts:
        litTestArgs += (' --param=' + key + '=' + lit_extra_opts[key])

    cmake_opts = [properties.WithProperties('-DLLVM_LIT_ARGS='+litTestArgs)]
    for key in cmake_extra_opts:
        cmake_opts.append('-D' + key + '=' + cmake_extra_opts[key])

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
        haltOnFailure=False, workdir=src_root))
    f.addStep(buildbot.steps.shell.ShellCommand(
        name='make.builddir', command=['mkdir', build_path],
        haltOnFailure=True, workdir=src_root))

    f.addStep(buildbot.steps.shell.ShellCommand(
        name='cmake', command=['cmake', src_root] + cmake_opts,
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
        command         = ['make', jobs_flag, 'check-libcxxabi'],
        description     = ['testing', 'libcxxabi'],
        descriptionDone = ['test', 'libcxxabi'],
        workdir         = build_path))

    # Test libc++
    f.addStep(LitTestCommand(
        name            = 'test.libcxx',
        command         = ['make', jobs_flag, 'check-libcxx'],
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
