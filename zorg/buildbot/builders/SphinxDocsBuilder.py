from zorg.buildbot.builders import UnifiedTreeBuilder
from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand

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
