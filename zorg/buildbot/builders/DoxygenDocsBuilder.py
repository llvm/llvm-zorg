from collections import OrderedDict
from importlib import reload

from buildbot.plugins import steps, util
from buildbot.steps.shell import ShellCommand

from zorg.buildbot.builders import UnifiedTreeBuilder
from zorg.buildbot.commands import CmakeCommand

from zorg.buildbot.process import factory
reload(factory)
reload(UnifiedTreeBuilder)
reload(CmakeCommand)

llvm_docs = OrderedDict([
  # Project             Build target     Local path                                    Remote path
  ("llvm",              ("doxygen",      "docs/doxygen/html/",                         "llvm")),
  ("clang",             (None,           "tools/clang/docs/doxygen/html/",             "cfe")),
  ("clang-tools-extra", (None,           "tools/clang/tools/extra/docs/doxygen/html/", "cfe-extra")),
  ("flang",             (None,           "tools/flang/docs/doxygen/html/",             "flang")),
  ("polly",             (None,           "tools/polly/docs/doxygen/html/",             "polly")),
  ("openmp",            (None,           "projects/openmp/docs/doxygen/html/",         "openmp")),
  ("lldb",              ("lldb-cpp-doc", "tools/lldb/docs/cpp_reference/",             "lldb/cpp_reference")),
  # NOTE: 5/9/2020 lldb-python-doc fails to build. Disabled till be fixed.
  #(None,   ("lldb-python-doc",         "tools/lldb/docs/python_reference/",  "lldb")),
])

def getLLVMDocsBuildFactory(
        clean = True,
        depends_on_projects = None,
        extra_configure_args = None,
        timeout=10800,
        env = None,
        **kwargs):

    if depends_on_projects is None:
        # All the projects from llvm_docs, and remove all duplicates.
        _depends_on_projects=list(set(
            [project for project in llvm_docs if project]))
    else:
        # Make a local copy of depends_on_projects, as we are going to modify
        # that.
        _depends_on_projects=depends_on_projects[:]
        # Some projects are interdependent for the purpose of documentation.
        # Enforce the dependencies.
        # TODO: Check later the dependencies for doxygen docs and enforce them
        # here if needed.

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Be cautious and disable color output from all tools.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    CmakeCommand.CmakeCommand.applyDefaultOptions(cmake_args, [
        ("-G",                                "Ninja"),
        ("-DLLVM_ENABLE_DOXYGEN=",            "ON"),
        ("-DLLVM_BUILD_DOCS=",                "ON"),
        ("-DCLANG_TOOLS_EXTRA_INCLUDE_DOCS=", "ON"),
        ("-DLLVM_ENABLE_ASSERTIONS=",         "OFF"),
        ("-DCMAKE_BUILD_TYPE=",               "Release"),
        ])

    f = UnifiedTreeBuilder.getCmakeBuildFactory(
            clean=clean,
            depends_on_projects=_depends_on_projects,
            enable_runtimes=[], # Docs don't support runtimes build yet.
            extra_configure_args=cmake_args,
            env=merged_env,
            **kwargs) # Pass through all the extra arguments.

    # Build the documentation for all the projects.
    for project in llvm_docs:
        target = llvm_docs[project][0]

        # Build only those with specifies targets.
        if target:
            UnifiedTreeBuilder.addNinjaSteps(
                f,
                # Doxygen builds the final result for really
                # long time without any output.
                # We have to have a long timeout at this step.
                timeout=timeout,
                targets=[target],
                checks=[],
                env=merged_env,
                **kwargs)

    # Publish just built documentation
    for project in llvm_docs:
        target, local_path, remote_path = llvm_docs[project]

        f.addStep(
            ShellCommand(
                name="Publish {}".format(project or target),
                description=[
                    "Publish", "just", "built", "documentation", "for",
                    "{}".format(project or target)
                    ],
                command=[
                    'rsync',
                    '-vrl',
                    '--delete', '--force', '--delay-updates', '--delete-delay',
                    '--ignore-times',
                    '--checksum',
                    '-p', '--chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rw,Fg=rw,Fo=r',
                    "{}".format(local_path),
                    "lists.llvm.org:web/doxygen/{}".format(remote_path),
                    ],
                env=merged_env,
            )
        )

    return f
