from collections import OrderedDict
from importlib import reload

from buildbot.plugins import steps, util
from buildbot.steps.shell import ShellCommand
from buildbot.steps.cmake import CMake

from zorg.buildbot.builders import UnifiedTreeBuilder
from zorg.buildbot.commands import CmakeCommand

reload(UnifiedTreeBuilder)
reload(CmakeCommand)

llvm_docs = OrderedDict([
  # Project             Build target       Local path                                    Remote path
  ("llvm",              ("doxygen",        "docs/doxygen/html/",                         "llvm")),
  ("clang",             (None,             "tools/clang/docs/doxygen/html/",             "cfe")),
  ("clang-tools-extra", (None,             "tools/clang/tools/extra/docs/doxygen/html/", "cfe-extra")),
  ("flang",             (None,             "tools/flang/docs/doxygen/html/",             "flang")),
  ("polly",             (None,             "tools/polly/docs/doxygen/html/",             "polly")),
  ("openmp",            ("doxygen-openmp", "openmp/docs/doxygen/html/",                  "openmp")),
  ("lldb",              ("lldb-cpp-doc",   "tools/lldb/docs/cpp_reference/",             "lldb/cpp_reference")),
  # NOTE: 5/9/2020 lldb-python-doc fails to build. Disabled till be fixed.
  #(None,   ("lldb-python-doc",         "tools/lldb/docs/python_reference/",  "lldb")),
])

# The following we build as runtimes, everything else as projects.
runtimes = frozenset([
    "openmp",
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
        _depends_on_projects=set(
            [project for project in llvm_docs if project])
    else:
        _depends_on_projects=set(depends_on_projects).intersection(llvm_docs)
        # Some projects might be interdependent for the documentation purpose.
        # If so enforce the dependencies.
        # TODO: Check later the dependencies for doxygen docs and enforce them
        # here if needed.

    # Split _depends_on_projects to two lists: projects and runtimes
    _runtimes = runtimes.intersection(_depends_on_projects)
    _projects = _depends_on_projects.difference(_runtimes) or set("llvm")

    # Make a local copy of the configure args, as we are going to modify that.
    if extra_configure_args:
        cmake_args_projects = extra_configure_args[:]
        cmake_args_runtimes = extra_configure_args[:]
    else:
        cmake_args_projects = list()
        cmake_args_runtimes = list()

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Be cautious and disable color output from all tools.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    # Handle the projects first.
    CmakeCommand.CmakeCommand.applyDefaultOptions(cmake_args_projects, [
        ("-G",                                "Ninja"),
        ("-DLLVM_ENABLE_DOXYGEN=",            "ON"),
        ("-DLLVM_BUILD_DOCS=",                "ON"),
        ("-DCLANG_TOOLS_EXTRA_INCLUDE_DOCS=", "ON"),
        ("-DLLVM_ENABLE_ASSERTIONS=",         "OFF"),
        ("-DCMAKE_BUILD_TYPE=",               "Release"),
        ])

    # Projects are built in build/projects, and runtimes are built in
    # build/runtimes respectively.
    _project_obj_dir = "build/projects"
    _runtimes_obj_dir = "build/runtimes"

    f = UnifiedTreeBuilder.getLLVMBuildFactoryAndSourcecodeSteps(
            depends_on_projects=list(_depends_on_projects),
            enable_projects=_projects,
            enable_runtimes=[], # Runtimes are handled separately.
            obj_dir=_project_obj_dir,
            env=merged_env,
            **kwargs) # Pass through all the extra arguments.

    # Configure projects docs
    UnifiedTreeBuilder.addCmakeSteps(
        f,
        cleanBuildRequested=True,
        obj_dir=_project_obj_dir,
        extra_configure_args=cmake_args_projects,
        env=merged_env,
        **kwargs)

    # Build the documentation for all the projects.
    # Build only those with specified targets.
    for target in sorted([llvm_docs[p][0] for p in _projects if llvm_docs[p][0]]):
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

    # Clean up the runtimes build directory
    f.addStep(steps.RemoveDirectory(name=f'clean-{_runtimes_obj_dir}-dir',
              dir=_runtimes_obj_dir,
              haltOnFailure=False,
              flunkOnFailure=False,
              ))

    if _runtimes:
        # Clean up the runtimes build directory
        f.addStep(steps.RemoveDirectory(name=f'clean-{_runtimes_obj_dir}-dir',
                  dir=_runtimes_obj_dir,
                  haltOnFailure=False,
                  flunkOnFailure=False,
                  ))

        CmakeCommand.CmakeCommand.applyDefaultOptions(cmake_args_runtimes, [
            ("-G",                                "Ninja"),
            ("-DLLVM_ENABLE_DOXYGEN=",            "ON"),
            ("-DLLVM_BUILD_DOCS=",                "ON"),
            ("-DLLVM_INCLUDE_DOCS=",              "ON"),
            ("-DLLVM_ENABLE_ASSERTIONS=",         "OFF"),
            ("-DCMAKE_BUILD_TYPE=",               "Release"),
            ])

        # Prepare cmake params
        definitions = dict()
        options = list()
        for d in  cmake_args_runtimes:
            if isinstance(d, str) and d.startswith("-D"):
                k,v = d[2:].split('=', 1)
                definitions[k] = v
            else:
                options.append(d)
        definitions["LLVM_ENABLE_RUNTIMES"] = ";".join(_runtimes)
        _runtimes_src_dir = "../../llvm-project/runtimes"

        f.addStep(CMake(name="cmake-configure-runtimes",
                        haltOnFailure=True,
                        description=["Cmake", "configure", "runtimes", "docs"],
                        generator='Ninja',
                        definitions=definitions,
                        options=options,
                        path=_runtimes_src_dir,
                        env=merged_env,
                        workdir=_runtimes_obj_dir,
                        ))

        # Build the documentation for all the runtimes.
        # Build only those with specifies targets.
        for target in sorted([llvm_docs[p][0] for p in _runtimes if llvm_docs[p][0]]):
            UnifiedTreeBuilder.addNinjaSteps(
                f,
                obj_dir=_runtimes_obj_dir,
                targets=[target],
                checks=[],
                env=merged_env,
                **kwargs)

    # Publish just built documentation
    for p in sorted(_depends_on_projects):
        target, local_path, remote_path = llvm_docs[p]
        build_dir = _project_obj_dir if p in _projects else _runtimes_obj_dir
        doc = p or target

        f.addStep(
            ShellCommand(
                name="Publish {}".format(doc),
                description=[
                    "Publish", "just", "built", "documentation", "for",
                    "{}".format(doc)
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
                workdir=build_dir,
            )
        )

    return f
