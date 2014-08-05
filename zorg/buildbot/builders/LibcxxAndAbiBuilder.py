import os

import buildbot
import buildbot.process.factory
import buildbot.steps.shell
import buildbot.process.properties as properties

from buildbot.steps.source.svn import SVN

import zorg.buildbot.commands.LitTestCommand as lit_test_command
import zorg.buildbot.util.artifacts as artifacts
import zorg.buildbot.util.phasedbuilderutils as phased_builder_utils

reload(lit_test_command)
reload(artifacts)
reload(phased_builder_utils)


def getLibcxxWholeTree(f, src_root):
    llvm_path = src_root
    libcxx_path = os.path.join(llvm_path, 'projects/libcxx')
    libcxxabi_path = os.path.join(llvm_path, 'projects/libcxxabi')

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
    return f


def getLibcxxAndAbiBuilder(f=None, env={}):
    if f is None:
        f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(
        name="get_builddir",
        command=["pwd"],
        property="builddir",
        description="set build dir",
        workdir="."))

    src_root = os.path.join(properties.Property('builddir'), 'llvm')
    build_path = os.path.join(properties.Property('builddir'), 'build')

    f = getLibcxxWholeTree(f, src_root)

    # Nuke/remake build directory and run CMake
    f.addStep(buildbot.steps.shell.ShellCommand(
        name='rm.builddir', command=['rm', '-rf', build_path],
        haltOnFailure=False, workdir=src_root))
    f.addStep(buildbot.steps.shell.ShellCommand(
        name='make.builddir', command=['mkdir', build_path],
        haltOnFailure=True, workdir=src_root))

    f.addStep(buildbot.steps.shell.ShellCommand(
        name='cmake', command=['cmake', src_root], haltOnFailure=True,
        workdir=build_path, env=env))

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
    f.addStep(buildbot.steps.shell.ShellCommand(
        name='test.libcxxabi', command=['make', 'check-libcxxabi'],
        workdir=build_path))

    # Test libc++
    f.addStep(buildbot.steps.shell.ShellCommand(
        name='test.libcxx', command=['make', 'check-libcxx'],
        workdir=build_path))

    return f
