import os
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import ShellCommand
from buildbot.process.properties import WithProperties
from zorg.buildbot.commands.NinjaCommand import NinjaCommand

def getSphinxDocsBuildFactory(
        llvm_html         = False, # Build LLVM HTML documentation
        llvm_man          = False, # Build LLVM man pages
        clang_html        = False, # Build Clang HTML documentation
        clang_tools_html  = False, # Build Clang Extra Tools HTML documentation
        lld_html          = False, # Build LLD HTML documentation
        libcxx_html       = False  # Build Libc++ HTML documentation
        ):

    f = buildbot.process.factory.BuildFactory()

    llvm_srcdir = 'llvm/src'
    llvm_objdir = 'llvm/build'
    clang_srcdir = llvm_srcdir + '/tools/clang'
    clang_tools_srcdir = llvm_srcdir + '/tools/clang/tools/extra'
    lld_srcdir = llvm_srcdir + '/tools/lld'
    libcxx_srcdir = llvm_srcdir + '/projects/libcxx'
    libcxxabi_srcdir = llvm_srcdir + '/projects/libcxxabi'

    # Get LLVM. This is essential for all builds
    # because we build all subprojects in tree
    f.addStep(SVN(name='svn-llvm',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvm_srcdir))

    if clang_html:
        f.addStep(SVN(name='svn-clang',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/cfe/',
                      defaultBranch='trunk',
                      workdir=clang_srcdir))

    if clang_tools_html:
        f.addStep(SVN(name='svn-clang-tools',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/clang-tools-extra/',
                      defaultBranch='trunk',
                      workdir=clang_tools_srcdir))

    if lld_html:
        f.addStep(SVN(name='svn-lld',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/lld/',
                      defaultBranch='trunk',
                      workdir=lld_srcdir))

    if libcxx_html:
        f.addStep(SVN(name='svn-libcxx',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/libcxx/',
                      defaultBranch='trunk',
                      workdir=libcxx_srcdir))
        f.addStep(SVN(name='svn-libcxxabi',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/libcxxabi/',
                      defaultBranch='trunk',
                      workdir=libcxxabi_srcdir))

    f.addStep(ShellCommand(name="create-build-dir",
                               command=["mkdir", "-p", llvm_objdir],
                               haltOnFailure=False, # We might of already created the directory in a previous build
                               description=["create build dir"],
                               workdir="."))

    # Use CMake to configure
    cmakeCommand = [ "cmake",
                     WithProperties('%s/' + llvm_srcdir, 'workdir'),
                     '-G', 'Ninja',
                     '-DLLVM_ENABLE_SPHINX:BOOL=ON',
                     '-DSPHINX_OUTPUT_HTML:BOOL=ON',
                     '-DSPHINX_OUTPUT_MAN:BOOL=ON'
                   ]
    f.addStep(ShellCommand(name="cmake-configure",
                               command=cmakeCommand,
                               description=["cmake configure"],
                               workdir=llvm_objdir))

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

    if libcxx_html:
        f.addStep(NinjaCommand(name="docs-libcxx-html",
                               haltOnFailure=True,
                               description=["Build Libc++ Sphinx HTML documentation"],
                               workdir=llvm_objdir,
                               targets=['docs-libcxx-html']
                              ))

    return f
