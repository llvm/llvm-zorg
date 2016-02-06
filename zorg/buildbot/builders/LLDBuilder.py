import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import ShellCommand, SetProperty
from buildbot.steps.slave import RemoveDirectory
from buildbot.process.properties import WithProperties, Property
from zorg.buildbot.builders.Util import getVisualStudioEnvironment
from zorg.buildbot.builders.Util import extractSlaveEnvironment
from zorg.buildbot.commands.NinjaCommand import NinjaCommand

def getLLDBuildFactory(
           clean = True,
           jobs  = "%(jobs)s",
           extra_configure_args=[],
           env   = {}):

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
                   'CC'   : "clang",
                   'CXX'  : "clang++",
                   'TERM' : 'dumb'     # Be cautious and disable color output from all tools.
                 }
    if env is not None:
        merged_env.update(env)  # Overwrite pre-set items with the given ones, so user can set anything.

    llvm_srcdir = "llvm.src"
    llvm_objdir = "llvm.obj"

    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               env=merged_env,
                                               workdir="."))
    # Get LLVM and Lld
    f.addStep(SVN(name='svn-llvm',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvm_srcdir))
    f.addStep(SVN(name='svn-lld',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/lld/',
                  defaultBranch='trunk',
                  workdir='%s/tools/lld' % llvm_srcdir))

    # Clean directory, if requested.
    if clean:
        f.addStep(ShellCommand(name="rm-llvm_objdir",
                               command=["rm", "-rf", llvm_objdir],
                               haltOnFailure=True,
                               description=["rm build dir", "llvm"],
                               workdir="."))

    # Create configuration files with cmake
    f.addStep(ShellCommand(name="create-build-dir",
                               command=["mkdir", "-p", llvm_objdir],
                               haltOnFailure=False,
                               description=["create build dir"],
                               workdir="."))

    cmakeCommand = ["cmake"]
    # Reconsile configure args with the defaults we want.
    if not any(a.startswith('-DCMAKE_BUILD_TYPE=')   for a in extra_configure_args):
        cmakeCommand.append('-DCMAKE_BUILD_TYPE=Release')
    if not any(a.startswith('-DLLVM_ENABLE_WERROR=') for a in extra_configure_args):
        cmakeCommand.append('-DLLVM_ENABLE_WERROR=ON')
    cmakeCommand += extra_configure_args + ["../%s" % llvm_srcdir]

    # Note: ShellCommand does not pass the params with special symbols right.
    # The " ".join is a workaround for this bug.
    f.addStep(ShellCommand(name="cmake-configure",
                               description=["cmake configure"],
                               haltOnFailure=True,
                               command=WithProperties(" ".join(cmakeCommand)),
                               env=merged_env,
                               workdir=llvm_objdir))
    # Build Lld
    f.addStep(ShellCommand(name="build_Lld",
                               command=['nice', '-n', '10',
                                        'make', WithProperties("-j%s" % jobs)],
                               haltOnFailure=True,
                               description=["build lld"],
                               env=merged_env,
                               workdir=llvm_objdir))
    # Test Lld
    f.addStep(ShellCommand(name="test_lld",
                               command=["make", "lld-test"],
                               haltOnFailure=True,
                               description=["test lld"],
                               env=merged_env,
                               workdir=llvm_objdir))

    return f


def getLLDWinBuildFactory(
           clean = True,

           # Default values for VS devenv and build configuration
           vs = r"""%VS140COMNTOOLS%""",   # Visual Studio 2015.
           target_arch = None,             # Native.

           extra_configure_args=[],
           env   = {}):

    llvm_srcdir = "llvm.src"
    llvm_objdir = "llvm.obj"

    f = buildbot.process.factory.BuildFactory()

    # Get LLVM and Lld
    f.addStep(SVN(name='svn-llvm',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvm_srcdir))
    f.addStep(SVN(name='svn-lld',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/lld/',
                  defaultBranch='trunk',
                  workdir='%s/tools/lld' % llvm_srcdir))

    # Clean directory, if requested.
    cleanBuildRequested = lambda step: step.build.getProperty("clean") or clean
    f.addStep(RemoveDirectory(name='clean '+llvm_objdir,
                dir=llvm_objdir,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=cleanBuildRequested
                ))

    f.addStep(ShellCommand(name="create-build-dir",
                command=["if", "not", "exist", llvm_objdir,
                         "mkdir", llvm_objdir],
                haltOnFailure=True,
                description=["create build dir"],
                workdir="."))

    # Is CMake configuration already done?
    checkCMakeCommand = [
        "dir", "CMakeCache.txt", ">", "NUL",
        "&&", "echo", "Yes",
        "||", "echo", "No", ">", "NUL"]

    # Note: ShellCommand does not pass the params with special symbols right.
    # The " ".join is a workaround for this bug.
    f.addStep(SetProperty(name="CMake_done",
                          workdir=llvm_objdir,
                          command=WithProperties(" ".join(checkCMakeCommand)),
                                   #"cmd", "/C",
                                   #" ".join(checkCMakeCommand)],
                          haltOnFailure=True,
                          description=["check CMake_done"],
                          property="CMake_done"))

    # If set up environment step is requested, do this now.
    if vs:
        f.addStep(SetProperty(
            command=getVisualStudioEnvironment(vs, target_arch),
            extract_fn=extractSlaveEnvironment))
        assert not env, "Can't have custom builder env vars with VS"
        env = Property('slave_env')

    # Always build with ninja.
    cmakeCommand = ["cmake", "-G", "Ninja"]
    # Reconsile configure args with the defaults we want.
    if not any(a.startswith('-DCMAKE_BUILD_TYPE=')   for a in extra_configure_args):
        cmakeCommand.append('-DCMAKE_BUILD_TYPE=Release')
    if not any(a.startswith('-DLLVM_ENABLE_WERROR=') for a in extra_configure_args):
        cmakeCommand.append('-DLLVM_ENABLE_WERROR=ON')
    if not any(a.startswith('-DLLVM_ENABLE_ASSERTIONS=') for a in extra_configure_args):
        cmakeCommand.append('-DLLVM_ENABLE_ASSERTIONS=ON')
    if not any(a.startswith('-DLLVM_LIT_ARGS=') for a in extra_configure_args):
        cmakeCommand.append('-DLLVM_LIT_ARGS=\"-v\"')

    cmakeCommand += extra_configure_args + ["../%s" % llvm_srcdir]

    # Note: ShellCommand does not pass the params with special symbols right.
    # The " ".join is a workaround for this bug.
    f.addStep(ShellCommand(
        name="cmake-configure",
        description=["cmake configure"],
        haltOnFailure=True,
        command=WithProperties(" ".join(cmakeCommand)),
        env=env,
        workdir=llvm_objdir,
        doStepIf=lambda step: step.build.getProperty("CMake_done") != "Yes"))

    # Build Lld.
    f.addStep(NinjaCommand(name='build lld',
                           haltOnFailure=True,
                           description='build lld',
                           workdir=llvm_objdir,
                           env=env))

    # Test Lld
    f.addStep(NinjaCommand(name='test lld',
                           targets=['lld-test'],
                           haltOnFailure=True,
                           description='test lld',
                           workdir=llvm_objdir,
                           env=env))

    return f
