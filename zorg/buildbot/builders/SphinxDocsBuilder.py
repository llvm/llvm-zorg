import os
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import ShellCommand
from buildbot.process.properties import WithProperties
from zorg.buildbot.commands.NinjaCommand import NinjaCommand

def getSphinxDocsBuildFactory(
        llvm_html  = False, # Build LLVM HTML documentation
        llvm_man   = False, # Build LLVM man pages
        clang_html = False, # Build Clang HTML documentation
        lld_html   = False  # Build LLD HTML documentation
        ):

    f = buildbot.process.factory.BuildFactory()

    llvm_srcdir = 'llvm/src'
    llvm_objdir = 'llvm/build'
    clang_srcdir = llvm_srcdir + '/tools/clang'
    lld_srcdir = llvm_srcdir + '/tools/lld'

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

    if lld_html:
        f.addStep(SVN(name='svn-lld',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/lld/',
                      defaultBranch='trunk',
                      workdir=lld_srcdir))

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

    if lld_html:
        f.addStep(NinjaCommand(name="docs-lld-html",
                               haltOnFailure=True,
                               description=["Build LLD Sphinx HTML documentation"],
                               workdir=llvm_objdir,
                               targets=['docs-lld-html']
                              ))

    return f
