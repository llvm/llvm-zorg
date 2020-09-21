import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.process.properties import WithProperties
from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand
from zorg.buildbot.builders import UnifiedTreeBuilder
from zorg.buildbot.process.factory import LLVMBuildFactory

def getOpenMPCMakeBuildFactory(
        jobs                = '%(jobs)s',   # Number of concurrent jobs.
        clean               = True,         # "clean" step is requested if true
        env                 = None,         # Environmental variables for all steps.
        ompt                = False,        # Whether to enable the OpenMP Tools Interface.
        test                = True,         # Test the built libraries.
        depends_on_projects = None,
        **kwargs):

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Make sure Clang doesn't use color escape sequences.
                 }
    # Overwrite pre-set items with the given ones, so user can set anything.
    if env is not None:
        merged_env.update(env)

    llvm_srcdir = 'llvm.src'
    llvm_builddir = 'llvm.build'

    cleanBuildRequested = lambda step: clean or step.build.getProperty("clean", default=step.build.getProperty("clean_obj"))

    if depends_on_projects is None:
        # Monorepo configuration requires llvm and clang to get cmake work.
        depends_on_projects = ['llvm', 'clang', 'openmp']

    f = UnifiedTreeBuilder.getLLVMBuildFactoryAndSourcecodeSteps(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=llvm_builddir,
            cleanBuildRequested=cleanBuildRequested,
            env=merged_env,
            **kwargs) # Pass through all the extra arguments.

    f.addStep(
        ShellCommand(
            name            = 'clean',
            command         = ['rm', '-rf', f.obj_dir],
            warnOnFailure   = True,
            description     = ['clean'],
            doStepIf        = cleanBuildRequested,
            workdir         = '.',
            env             = merged_env))

    # Configure LLVM and OpenMP (and Clang, if requested).
    cmake_args  = ['cmake', '-G', 'Ninja']
    cmake_args += ['-DCMAKE_BUILD_TYPE=Release', '-DLLVM_ENABLE_ASSERTIONS=ON']
    if ompt:
        cmake_args += ['-DLIBOMP_OMPT_SUPPORT=ON']
    if test:
        lit_args = '-vv --show-unsupported --show-xfail -j %s' % jobs
        cmake_args += [WithProperties('-DLLVM_LIT_ARGS=%s' % lit_args)]

    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-DLLVM_ENABLE_PROJECTS=', ";".join(f.depends_on_projects)),
        ])

    # Add llvm-lit and clang (if built) to PATH
    merged_env.update({
        'PATH': WithProperties('%(workdir)s/' + llvm_builddir + '/bin:${PATH}')})

    src_dir = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, f.obj_dir)

    f.addStep(CmakeCommand(name='configure-openmp',
                           description=['configure','openmp'],
                           options=cmake_args,
                           path=src_dir,
                           env=merged_env,
                           workdir=f.obj_dir,
                           haltOnFailure=True,
                           **kwargs # Pass through all the extra arguments.
                           ))

    # Build OpenMP runtime libraries.
    f.addStep(
        NinjaCommand(
            name        = 'compile-openmp',
            description = 'compile openmp',
            workdir     = f.obj_dir,
            env         = merged_env,
            haltOnFailure=True))

    # Test OpenMP runtime libraries, if requested.
    if test:
        # Add llvm-lit and clang (if built) to PATH
        merged_env.update({
            'PATH': WithProperties('%(workdir)s/' + llvm_builddir + '/bin:${PATH}')})

        ninja_test_args = ['ninja', WithProperties('-j %s' % jobs)]
        f.addStep(
            LitTestCommand(
                name        = 'test-openmp',
                command     = ninja_test_args + ['check-openmp'],
                description = 'test openmp',
                workdir     = f.obj_dir,
                env         = merged_env,
                haltOnFailure=True))

    return f
