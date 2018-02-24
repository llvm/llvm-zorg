from buildbot.process.properties import WithProperties
from buildbot.steps.shell import ShellCommand

from zorg.buildbot.builders import UnifiedTreeBuilder
from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand

def getFactory(
        depends_on_projects = None,
        targets = None,
        checks = None,
        clean = False,
        extra_configure_args = None,
        env = None,
        **kwargs):

    # Prepare environmental variables. Set here all env we want for all steps.
    merged_env = {
        'TERM' : 'dumb' # Make sure Clang doesn't use color escape sequences.
        }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    if depends_on_projects:
        depends_on_projects = list(depends_on_projects)
    else:
        depends_on_projects = ['llvm', 'lld']

    if checks is None:
        checks = [] # No check unless requested specifically.

    if extra_configure_args is None:
        cmake_args = list()
    else:
        cmake_args = list(extra_configure_args)

    # Some options are required for this build no matter what.
    CmakeCommand.applyRequiredOptions(cmake_args, [
        ('-G', 'Ninja'),
        ('-DLLVM_OPTIMIZED_TABLEGEN=', 'OFF'),
        ('-DLLVM_BUILD_STATIC=',       'ON'),
        ('-DLLVM_ENABLE_PIC=',         'OFF'),
        ])

    f = UnifiedTreeBuilder.getCmakeBuildFactory(
            depends_on_projects=depends_on_projects,
            clean=clean,
            extra_configure_args=cmake_args,
            env=merged_env,
            **kwargs) # Pass through all the extra arguments.

    if targets:
        step_name = "build-%s" % ("-".join(targets))
        step_description=["Build"]
        step_description.extend(targets)
    else:
        step_name = "build-unified-tree"
        step_description=["Build", "unified", "tree"]

    f.addStep(NinjaCommand(name=step_name,
                           targets=targets,
                           description=step_description,
                           haltOnFailure=kwargs.get('haltOnFailure', True),
                           env=merged_env,
                           workdir=f.obj_dir,
                           **kwargs # Pass through all the extra arguments.
                           ))

    # Test just built components if requested.
    if checks:
        f.addStep(NinjaCommand(name="test-%s" % ("-".join(checks)),
                               targets=checks,
                               description=[
                                   "Test", "just", "built", "components"],
                               haltOnFailure=kwargs.get('haltOnFailure', True),
                               env=merged_env,
                               workdir=f.obj_dir,
                               **kwargs # Pass through all the extra arguments.
                               ))

    # Copy just built LLD executable to the test suite directory
    # to avoid load from a hard drive overhead.
    f.addStep(
        ShellCommand(
            name="copy-lld-to-test-suite",
            description=[
                "Copy", "LLD", "executable", "to", "the", "performance",
                "test", "suite",
                ],
            command=[
                "cp", "-aL", "./bin/ld.lld", "../lld-speed-test/ld.lld"
                ],
            workdir=f.obj_dir,
            env=merged_env
        )
    )

    # Run the performance test suite.
    perf_command = [
        "python",
        "%(workdir)s/lld-benchmark.py",
        "--machine=%(slavename)s",
        "--revision=%(got_revision)s",
        "--linker=./ld.lld",
        ".",
        ]

    f.addStep(
        ShellCommand(
            name="performance-test-suite",
            description=[
                "LLD", "performance","test","suite",
                ],
            command=WithProperties(" ".join(perf_command)),
            workdir="./lld-speed-test",
            env=merged_env
        )
    )

    return f
