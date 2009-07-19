import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.steps.transfer import FileDownload
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.DejaGNUCommand import DejaGNUCommand
from zorg.buildbot.commands.ClangTestCommand import ClangTestCommand
from zorg.buildbot.commands.GTestCommand import GTestCommand

def getClangBuildFactory(triple, 
                         CC='gcc', CXX='g++', 
                         CFLAGS='', CXXFLAGS='',
                         useCMake=False,
                         extraMakeArgs=''):
    f = buildbot.process.factory.BuildFactory()
    f.addStep(SVN(name='svn-llvm',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir='llvm'))
    f.addStep(SVN(name='svn-clang',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/cfe/', 
                  defaultBranch='trunk',
                  workdir='llvm/tools/clang'))
    if useCMake:
        builddir = 'llvm/build'
        f.addStep(Configure(command=['cmake',
                                     '-DCMAKE_C_COMPILER=%s' % (CC,),
                                     '-DCMAKE_CXX_COMPILER=%s' % (CXX,),
                                     '-DCMAKE_C_FLAGS=%s' % (CFLAGS,),
                                     '-DCMAKE_CXX_FLAGS=%s' % (CXXFLAGS,),
                                     '../'],
                            workdir=builddir,
                            description=['cmake','Debug'],
                            descriptionDone=['cmake','Debug']))
    else:
        builddir = 'llvm'
        f.addStep(Configure(command=['./configure',
                                     '--build', triple,
                                     'CC=%s %s' % (CC, CFLAGS),
                                     'CXX=%s %s' % (CXX, CXXFLAGS)],
                            workdir=builddir,
                            description=['configuring','Debug'],
                            descriptionDone=['configure','Debug']))
    f.addStep(WarningCountingShellCommand(name="clean-llvm", 
                                          command="make clean", 
                                          haltOnFailure=True, 
                                          description="cleaning llvm", 
                                          descriptionDone="clean llvm",
                                          workdir=builddir))
    f.addStep(WarningCountingShellCommand(name="compile", 
                                          command=WithProperties("nice -n 10 make -j%(jobs)d"), 
                                          haltOnFailure=True, 
                                          description="compiling llvm & clang", 
                                          descriptionDone="compile llvm & clang",
                                          workdir=builddir))
    if not useCMake: # :(
        f.addStep(DejaGNUCommand(name='test-llvm',
                                 workdir=builddir))
    if not useCMake: # :(
        f.addStep(ClangTestCommand(name='test-clang',
                                   command=WithProperties("nice -n 10 make -j%(jobs)d test VERBOSE=1"), 
                                   workdir="llvm/tools/clang"))
    if not useCMake: # :(
        f.addStep(GTestCommand(name="unittest-llvm", 
                               command=["make", "unittests"],
                               description="unittests (llvm)", 
                               workdir="llvm"))
    return f


def getClangMSVCBuildFactory():
    f = buildbot.process.factory.BuildFactory()

    if True:
        f.addStep(SVN(name='svn-llvm',
                      mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                      defaultBranch='trunk',
                      workdir='llvm'))

    if True:
        f.addStep(SVN(name='svn-clang',
                      mode='update', baseURL='http://llvm.org/svn/llvm-project/cfe/', 
                      defaultBranch='trunk',
                      workdir='llvm/tools/clang'))

    # Full & fast clean.
    if True:
        f.addStep(ShellCommand(name='clean-1',
                               command=['del','/s/q','build'],
                               warnOnFailure=True, 
                               description='cleaning',
                               descriptionDone='clean',
                               workdir='llvm'))
        f.addStep(ShellCommand(name='clean-2',
                               command=['rmdir','/s/q','build'],
                               warnOnFailure=True, 
                               description='cleaning',
                               descriptionDone='clean',
                               workdir='llvm'))

    # Create the project files.
    
    # FIXME: Don't require local versions of these files. See buildbot ticket
    # #595. We could always write the contents into a temp file, to avoid having
    # them in SVN, and to allow parameterization.
    f.addStep(FileDownload(mastersrc=os.path.join(os.path.dirname(__file__),
                                                  'ClangMSVC_cmakegen.bat'),
                           slavedest='cmakegen.bat',
                           workdir='llvm\\build'))
    f.addStep(ShellCommand(name='cmake',
                           command=['cmakegen.bat'],
                           haltOnFailure=True, 
                           description='cmake gen',
                           workdir='llvm\\build'))

    # Build it.
    f.addStep(FileDownload(mastersrc=os.path.join(os.path.dirname(__file__),
                                                  'ClangMSVC_vcbuild.bat'),
                           slavedest='vcbuild.bat',
                           workdir='llvm\\build'))
    f.addStep(WarningCountingShellCommand(name='vcbuild',
                                          command=['vcbuild.bat'],
                                          haltOnFailure=True, 
                                          description='vcbuild',
                                          workdir='llvm\\build',
                                          warningPattern=" warning C.*:"))
    return f
