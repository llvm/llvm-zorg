from collections import OrderedDict

from buildbot.steps.shell import ShellCommand

from zorg.buildbot.builders import UnifiedTreeBuilder
from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand

llvm_docs = OrderedDict([
  # Project              Build target             Local path                            Remote path
  ("llvm",              ("docs-llvm-html",        "docs/html/",                         "llvm")),
  ("clang",             ("docs-clang-html",       "tools/clang/docs/html/",             "cfe")),
  ("clang-tools-extra", ("docs-clang-tools-html", "tools/clang/tools/extra/docs/html/", "clang-tools-extra")),
  ("libcxx",            ("docs-libcxx-html",      "projects/libcxx/docs/html/",         "libcxx")),
  ("libunwind",         ("docs-libunwind-html",   "projects/libunwind/docs/html/",      "libunwind")),
  ("lld",               ("docs-lld-html",         "tools/lld/docs/html/",               "lld")),
  ("lldb",              ("docs-lldb-html",        "tools/lldb/docs/html/",              "lldb")),
  ('flang',             ("docs-flang-html",       "tools/flang/docs/html/",             "flang")),
  ("openmp",            ("docs-openmp-html",      "projects/openmp/docs/html/",         "openmp")),
  ("polly",             ("docs-polly-html",       "tools/polly/docs/html/",             "polly")),
])


def getSphinxDocsBuildFactory(
        llvm_html         = False, # Build LLVM HTML documentation
        llvm_man          = False, # Build LLVM man pages
        clang_html        = False, # Build Clang HTML documentation
        clang_tools_html  = False, # Build Clang Extra Tools HTML documentation
        lld_html          = False, # Build LLD HTML documentation
        libcxx_html       = False, # Build Libc++ HTML documentation
        libunwind_html    = False, # Build libunwind HTML documentation
        lldb_html         = False, # Build LLDB HTML documentation
        extra_configure_args = None,
        **kwargs):

    if extra_configure_args:
        cmake_args = extra_configure_args[:]
    else:
        cmake_args = list()

    # Set proper defaults for the config flags.
    CmakeCommand.applyDefaultOptions(cmake_args, [
      ('-G',                    'Ninja'),
      ('-DLLVM_ENABLE_SPHINX=', 'ON'),
      ('-DSPHINX_OUTPUT_HTML=', 'ON'),
      ('-DSPHINX_OUTPUT_MAN=',  'ON'),
      ('-DLLDB_INCLUDE_TESTS=', 'OFF'),
      ('-DLLVM_TEMPORARILY_ALLOW_OLD_TOOLCHAIN=', 'ON'),
      ('-DLLVM_ENABLE_ASSERTIONS=',  'OFF'),
      ])

    llvm_srcdir = 'llvm/src'
    llvm_objdir = 'llvm/build'

    depends_on_projects = ['llvm']
    if clang_html or clang_tools_html or lldb_html:
        depends_on_projects.append('clang')
    if clang_tools_html:
        depends_on_projects.append('clang-tools-extra')
    if lld_html:
        depends_on_projects.append('lld')
    if lldb_html:
        depends_on_projects.append('lldb')
    if libcxx_html:
        depends_on_projects.append('libcxx')
        depends_on_projects.append('libcxxabi')
    if libunwind_html:
        depends_on_projects.append('libunwind')

    f = UnifiedTreeBuilder.getCmakeBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir=llvm_srcdir,
            obj_dir=llvm_objdir,
            extra_configure_args=cmake_args,
            **kwargs) # Pass through all the extra arguments.

    if llvm_html:
        f.addStep(NinjaCommand(name="docs-llvm-html",
                               haltOnFailure=True,
                               description=["Build LLVM Sphinx HTML documentation"],
                               workdir=llvm_objdir,
                               targets=['docs-llvm-html']
                              ))

    if llvm_man:
        f.addStep(NinjaCommand(name="docs-llvm-man",
                               haltOnFailure=True,
                               description=["Build LLVM Sphinx man pages"],
                               workdir=llvm_objdir,
                               targets=['docs-llvm-man']
                              ))

    if clang_html:
        f.addStep(NinjaCommand(name="docs-clang-html",
                               haltOnFailure=True,
                               description=["Build Clang Sphinx HTML documentation"],
                               workdir=llvm_objdir,
                               targets=['docs-clang-html']
                              ))

    if clang_tools_html:
        f.addStep(NinjaCommand(name="docs-clang-tools-html",
                               haltOnFailure=True,
                               description=["Build Clang Extra Tools Sphinx HTML documentation"],
                               workdir=llvm_objdir,
                               targets=['docs-clang-tools-html']
                              ))

    if lld_html:
        f.addStep(NinjaCommand(name="docs-lld-html",
                               haltOnFailure=True,
                               description=["Build LLD Sphinx HTML documentation"],
                               workdir=llvm_objdir,
                               targets=['docs-lld-html']
                              ))

    if lldb_html:
        f.addStep(NinjaCommand(name="docs-lldb-html",
                               haltOnFailure=True,
                               description=["Build LLDB Sphinx HTML documentation"],
                               workdir=llvm_objdir,
                               targets=['docs-lldb-html']
                              ))

    if libcxx_html:
        f.addStep(NinjaCommand(name="docs-libcxx-html",
                               haltOnFailure=True,
                               description=["Build Libc++ Sphinx HTML documentation"],
                               workdir=llvm_objdir,
                               targets=['docs-libcxx-html']
                              ))

    if libunwind_html:
        f.addStep(NinjaCommand(name="docs-libunwind-html",
                               haltOnFailure=True,
                               description=["Build libunwind Sphinx HTML documentation"],
                               workdir=llvm_objdir,
                               targets=['docs-libunwind-html']
                              ))

    return f


def getLLVMDocsBuildFactory(
        clean = False,
        depends_on_projects = None,
        extra_configure_args = None,
        env = None,
        **kwargs):

    if depends_on_projects is None:
        # All the projects by default.
        _depends_on_projects=[
            "llvm",
            "clang",
            "clang-tools-extra",
            "libcxx",
            "libcxxabi",
            "libunwind",
            "lld",
            "lldb",
            "flang",
            "openmp",
            "polly",
        ]
    else:
        # Make a local copy of depends_on_projects, as we are going to modify
        # that.
        _depends_on_projects=depends_on_projects[:]
        # Some projects are interdependent for the purpose of documentation.
        # Enforce the dependencies.
        if ("clang-tools-extra" in _depends_on_projects or \
            "lldb" in _depends_on_projects
           ) and "clang" not in _depends_on_projects:
            _depends_on_projects.append("clang")
        if "libcxx" in _depends_on_projects and \
           "libcxxabi" not in _depends_on_projects:
            _depends_on_projects.append("libcxxabi")
        if "libcxxabi" in _depends_on_projects and \
           "libcxx" not in _depends_on_projects:
            _depends_on_projects.append("libcxx")

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

    CmakeCommand.applyDefaultOptions(cmake_args, [
        ("-G",                           "Ninja"),
        ("-DLLVM_ENABLE_SPHINX=",        "ON"),
        ("-DSPHINX_OUTPUT_HTML=",        "ON"),
        ("-DSPHINX_OUTPUT_MAN=",         "OFF"),
        ("-DSPHINX_WARNINGS_AS_ERRORS=", "OFF"),
        ("-DLLVM_ENABLE_ASSERTIONS=",    "OFF"),
        ("-DCMAKE_BUILD_TYPE=",          "Release"),
        ])

    # Build docs for each of the projects this builder depends on
    docs = [
        llvm_docs[project] for project in llvm_docs.keys()
        if project in _depends_on_projects
    ]

    f = UnifiedTreeBuilder.getCmakeBuildFactory(
            clean=clean,
            depends_on_projects=_depends_on_projects,
            extra_configure_args=cmake_args,
            env=merged_env,
            **kwargs) # Pass through all the extra arguments.

    UnifiedTreeBuilder.addNinjaSteps(
        f,
        targets=[d[0] for d in docs],
        checks=[],
        env=merged_env,
        **kwargs)

    # Publish just built documentation
    for target, local_path, remote_path in docs:
        f.addStep(
            ShellCommand(
                name="Publish %s" % target,
                description=[
                    "Publish", "just", "built", "documentation", "fior",
                    "%s" % target,
                    ],
                command=[
                    'rsync',
                    '-vrl',
                    '--delete', '--force', '--delay-updates', '--delete-delay',
                    '--ignore-times',
                    '--checksum',
                    '-p', '--chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rw,Fg=rw,Fo=r',
                    "%s" % local_path,
                    "lists.llvm.org:web/%s" % remote_path,
                    ],
                env=merged_env,
            )
        )

    return f
