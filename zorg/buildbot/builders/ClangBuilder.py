import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import Configure, WarningCountingShellCommand
from buildbot.process.properties import WithProperties

from zorg.buildbot.commands.DejaGNUCommand import DejaGNUCommand
from zorg.buildbot.commands.ClangTestCommand import ClangTestCommand
from zorg.buildbot.commands.GTestCommand import GTestCommand

def getClangBuildFactory(triple, 
                         CC='gcc', CXX='g++', 
                         useCMake=False):
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
                                     '-DCMAKE_C_COMPILER=%s' % (cc,),
                                     '-DCMAKE_CXX_COMPILER=%s' % (cxx,),
                                     '../'],
                            workdir=builddir,
                            description=['cmake','Debug'],
                            descriptionDone=['cmake','Debug']))
    else:
        builddir = 'llvm'
        f.addStep(Configure(command=['./configure',
                                     '--build', triple,
                                     'CC=%s' % (CC,),
                                     'CXX=%s' % (CXX,)],
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
    f.addStep(ClangTestCommand(name='test-clang',
                               command=WithProperties("nice -n 10 make -j%(jobs)d test VERBOSE=1"), 
                               workdir="llvm/tools/clang"))
    if not useCMake: # (
        f.addStep(GTestCommand(name="unittest-llvm", 
                               command=["make", "unittests"],
                               description="unittests (llvm)", 
                               workdir="llvm"))
    return f
