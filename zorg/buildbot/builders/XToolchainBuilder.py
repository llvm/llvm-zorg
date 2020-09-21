from buildbot.steps.shell import ShellCommand, SetProperty
from buildbot.process.properties import WithProperties, Property

from zorg.buildbot.process.properties import InterpolateToPosixPath
from zorg.buildbot.commands.CmakeCommand   import CmakeCommand
from zorg.buildbot.commands.NinjaCommand   import NinjaCommand
from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.process.factory         import LLVMBuildFactory

import zorg.buildbot.builders.Util as builders_util

def getCmakeWithMSVCBuildFactory(
        clean = True,                # False for incremental builds.
        depends_on_projects  = None, # List of projects to listen.
        cmake_cache = None,          # Path to a cmake cache file.
        extra_configure_args = None, # Extra CMake args if any.
        llvm_srcdir = None,          # Source code root directory.
        obj_dir = None,              # Build tree root directory.
        install_dir = None,          # Directory to install the results to.
        checks = None,               # List of checks to test the build.
        checks_on_target = None,     # [(<name>,[<command tokens>])] array of
                                     # check name and command to run on target.
        jobs = None,                 # Restrict a degree of parallelism.
        env  = None,                 # Environmental variables for all steps.
        # VS tools environment variable if using MSVC.
        # For example, "autodetect" to auto detect, %VS140COMNTOOLS% to select
        # the VS 2015 toolchain, or empty string if environment is already set.
        vs=None,
        **kwargs):

    if vs is None:
        # We autodetect Visual Studio, unless otherwise is requested.
        vs = "autodetect"

    if install_dir is None:
        install_dir = 'install'

    # Prepare environmental variables. Set here all env we want for all steps.
    merged_env = {
        'TERM' : 'dumb' # Make sure Clang doesn't use color escape sequences.
        }
    if env is not None:
        assert not vs, "Cannot have custom builder env vars with VS setup."
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    if depends_on_projects is None:
        depends_on_projects = [
            'llvm',
            'compiler-rt',
            'clang',
            'clang-tools-extra',
            'libunwind',
            'libcxx',
            'libcxxabi',
            'lld',
        ]

    if checks is None:
        # Check only host-side tools. Target-side tests should run on a target.
        checks=[
            "check-llvm",
            "check-clang",
            "check-lld",
        ]

    source_remove_requested = lambda step: step.build.getProperty("clean")
    clean_build_requested = lambda step: \
        clean or \
        step.build.getProperty("clean", \
            default=step.build.getProperty("clean_obj") \
        )

    f = LLVMBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=obj_dir,
            install_dir=install_dir,
            cleanBuildRequested=clean_build_requested,
            **kwargs) # Pass through all the extra arguments.

    # Remove the source code tree if requested.
    # NOTE: Somehow RemoveDirectory buildbot command often fails on Windows,
    # as somthing keeps a lock. We use rm command instead realying on a shell
    # to support that.
    f.addStep(ShellCommand(name='clean-%s-dir' % f.monorepo_dir,
                           command=['rm','-rf', f.monorepo_dir],
                           warnOnFailure=True,
                           haltOnFailure=False,
                           flunkOnFailure=False,
                           description='Remove the source code',
                           workdir='.',
                           env=merged_env,
                           doStepIf=source_remove_requested))

    # Get the source code.
    f.addGetSourcecodeSteps(**kwargs)

    # Remove the build directory if requested.
    f.addStep(ShellCommand(name='clean-%s-dir' % f.obj_dir,
                           command=['rm','-rf', f.obj_dir],
                           warnOnFailure=True,
                           haltOnFailure=False,
                           flunkOnFailure=False,
                           description='Remove build directory',
                           workdir='.',
                           env=merged_env,
                           doStepIf=clean_build_requested))

    if vs:
        # Configure MSVC environment if requested.
        f.addStep(SetProperty(
            command=builders_util.getVisualStudioEnvironment(vs, None),
            extract_fn=builders_util.extractSlaveEnvironment))
        merged_env = Property('slave_env')

    # Since this is a build of a cross toolchain, we build only the host-side
    # tools first by the host system compiler. Libraries will be cross-compiled.
    cmake_args.append(InterpolateToPosixPath(
        '-DLLVM_AR=%(workdir)s/' + f.obj_dir + '/bin/llvm-ar.exe')),

    CmakeCommand.applyDefaultOptions(cmake_args, [
        ('-G', 'Ninja'),
        ('-DLLVM_ENABLE_PROJECTS=', 'llvm;clang;clang-tools-extra;lld'),
        ('-DCMAKE_BUILD_TYPE=', 'Release'),
        ('-DCMAKE_CXX_FLAGS=', '-D__OPTIMIZE__'),
        ('-DLLVM_ENABLE_ASSERTIONS=', 'ON'),
        ('-DLLVM_LIT_ARGS=', '-v -vv'),
        ])

    if install_dir:
        install_dir_rel = LLVMBuildFactory.pathRelativeTo(
                              install_dir,
                              f.obj_dir)
        CmakeCommand.applyRequiredOptions(cmake_args, [
            ('-DCMAKE_INSTALL_PREFIX=', install_dir_rel),
            ])

    # Remove the build directory if requested.
    f.addStep(ShellCommand(name='clean-%s-dir' % install_dir,
                           command=['rm','-rf', install_dir],
                           warnOnFailure=True,
                           haltOnFailure=False,
                           flunkOnFailure=False,
                           description='Remove install directory',
                           workdir='.',
                           env=merged_env,
                           doStepIf=clean_build_requested))

    src_dir_rel = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, f.obj_dir)

    # Add given cmake cache at the very end.
    if cmake_cache:
        cmake_args.append('-C%s' % cmake_cache)

    f.addStep(CmakeCommand(name="cmake-configure",
                           haltOnFailure=True,
                           description=["Cmake", "configure"],
                           options=cmake_args,
                           path=src_dir_rel,
                           workdir=f.obj_dir,
                           env=merged_env,
                           **kwargs # Pass through all the extra arguments.
                           ))

    f.addStep(NinjaCommand(name="build-%s" % f.monorepo_dir,
                           haltOnFailure=True,
                           description=["Build", f.monorepo_dir],
                           workdir=f.obj_dir,
                           env=merged_env,
                           **kwargs # Pass through all the extra arguments.
                           ))

    # Test the components if requested one check at a time.
    for check in checks:
        f.addStep(
            LitTestCommand(
                haltOnFailure=False, # We want to test as much as we could.
                name='test-%s' % check,
                command=["ninja", WithProperties(check)],
                description=[
                    "Testing", "just", "built", "components", "for", check],
                descriptionDone=[
                    "Test", "just", "built", "components", "for", check,
                     "completed"],
                env=merged_env,
                **kwargs # Pass through all the extra arguments.
                ))

    # Run commands on a target if requested.
    if checks_on_target:
        for check, cmd in checks_on_target:
            f.addStep(
                LitTestCommand(
                    haltOnFailure=False, # We want to test as much as we could.
                    name='test-%s' % check,
                    command=cmd,
                    description=[
                        "Testing", "just", "built", "components", "for", check],
                    descriptionDone=[
                        "Test", "just", "built", "components", "for", check,
                        "completed"],
                    env=merged_env,
                    **kwargs # Pass through all the extra arguments.
                    ))

    # Install just built components
    if install_dir:
        f.addStep(NinjaCommand(name="install-all",
                               haltOnFailure=True,
                               targets=["install"],
                               description=[
                                   "Install", "just", "built", "components"],
                               workdir=f.obj_dir,
                               env=merged_env,
                               **kwargs # Pass through all the extra arguments.
                               ))

    return f
