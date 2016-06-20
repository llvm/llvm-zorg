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
from zorg.buildbot.conditions.FileConditions import FileDoesNotExist
from zorg.buildbot.process.factory import LLVMBuildFactory

def getLLDBuildFactory(
           clean = True,
           jobs  = None,
           extra_configure_args = None,
           env   = None):

    # Set defaults
    if jobs is None:
        jobs = "%(jobs)s"
    if extra_configure_args is None:
        extra_configure_args = []

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
                   'CC'   : "clang",
                   'CXX'  : "clang++",
                   'TERM' : 'dumb'     # Be cautious and disable color output from all tools.
                 }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    f = LLVMBuildFactory(
            depends_on_projects=['llvm', 'lld'],
            llvm_srcdir="llvm.src",
            llvm_objdir="llvm.obj")

    # Get LLVM and Lld
    f.addSVNSteps()

    # Clean directory, if requested.
    cleanBuildRequested = lambda step: step.build.getProperty("clean") or clean
    f.addStep(RemoveDirectory(name='clean ' + f.llvm_objdir,
              dir=f.llvm_objdir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested
              ))

    # Create configuration files with cmake
    cmakeCommand = ["cmake"]
    # Reconsile configure args with the defaults we want.
    if not any(a.startswith('-DCMAKE_BUILD_TYPE=')   for a in extra_configure_args):
        cmakeCommand.append('-DCMAKE_BUILD_TYPE=Release')
    if not any(a.startswith('-DLLVM_ENABLE_WERROR=') for a in extra_configure_args):
        cmakeCommand.append('-DLLVM_ENABLE_WERROR=ON')
    cmakeCommand += extra_configure_args + ["../%s" % f.llvm_srcdir]

    # Note: ShellCommand does not pass the params with special symbols right.
    # The " ".join is a workaround for this bug.
    f.addStep(ShellCommand(name="cmake-configure",
                           description=["cmake configure"],
                           haltOnFailure=False, # TODO: change to True
                           command=WithProperties(" ".join(cmakeCommand)),
                           env=merged_env,
                           workdir=f.llvm_objdir,
                           doStepIf=FileDoesNotExist("./%s/CMakeCache.txt" % f.llvm_objdir)))

    # Build Lld
    f.addStep(ShellCommand(name="build_Lld",
                           command=['nice', '-n', '10',
                                    'make', WithProperties("-j%s" % jobs)],
                           haltOnFailure=False, # TODO: change to True
                           description=["build lld"],
                           env=merged_env,
                           workdir=f.llvm_objdir))

    # Test Lld
    f.addStep(ShellCommand(name="test_lld",
                           command=["make", "lld-test"],
                           haltOnFailure=False, # TODO: change to True
                           description=["test lld"],
                           env=merged_env,
                           workdir=f.llvm_objdir))

    return f


def getLLDWinBuildFactory(
           clean = True,

           # Default values for VS devenv and build configuration
           vs = None,          # What to run to configure Visual Studio utils.
           target_arch = None, # Native.

           extra_configure_args = None,
           env   = None):

    # Set defaults
    if vs is None:
        vs = r"""%VS140COMNTOOLS%"""   # Visual Studio 2015.
    if extra_configure_args is None:
        extra_configure_args = []
    if env is None:
        env = {}

    f = LLVMBuildFactory(
            depends_on_projects=['llvm', 'lld'],
            llvm_srcdir="llvm.src",
            llvm_objdir="llvm.obj")

    # Get LLVM and Lld
    f.addSVNSteps()

    # Clean directory, if requested.
    cleanBuildRequested = lambda step: step.build.getProperty("clean") or clean
    f.addStep(RemoveDirectory(name='clean ' + f.llvm_objdir,
              dir=f.llvm_objdir,
              haltOnFailure=False,
              flunkOnFailure=False,
              doStepIf=cleanBuildRequested
              ))

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

    cmakeCommand += extra_configure_args + ["../%s" % f.llvm_srcdir]

    # Note: ShellCommand does not pass the params with special symbols right.
    # The " ".join is a workaround for this bug.
    f.addStep(ShellCommand(
        name="cmake-configure",
        description=["cmake configure"],
        haltOnFailure=True,
        warnOnWarnings=True,
        command=WithProperties(" ".join(cmakeCommand)),
        env=env,
        workdir=f.llvm_objdir,
        doStepIf=FileDoesNotExist("./%s/CMakeCache.txt" % f.llvm_objdir)))

    # Build Lld.
    f.addStep(NinjaCommand(name='build lld',
                           haltOnFailure=True,
                           warnOnWarnings=True,
                           description='build lld',
                           workdir=f.llvm_objdir,
                           env=env))

    # Test Lld
    f.addStep(NinjaCommand(name='test lld',
                           targets=['lld-test'],
                           haltOnFailure=True,
                           warnOnWarnings=True,
                           description='test lld',
                           workdir=f.llvm_objdir,
                           env=env))

    return f
