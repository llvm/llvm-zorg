from buildbot.scheduler import Scheduler
from buildbot.schedulers import triggerable
from buildbot.process.properties import WithProperties

def get_schedulers():

    vcScheduler = Scheduler(name='all',branch=None,
                                 treeStableTimer=2*60,
                                 builderNames=['phase1 - sanity',])
    startphase1 = triggerable.Triggerable(name='doPhase1',
                         builderNames=['clang-x86_64-osx10-gcc42-RA',])

    gate1 = triggerable.Triggerable(name='phase2',
                         builderNames=['phase2 - living',],
                         properties = {'revision':WithProperties('%(got_revision)s')})
    startphase2 = triggerable.Triggerable(name='doPhase2',
                         builderNames=[
                                       'nightly_clang-x86_64-osx10-gcc42-RA',
                                       'clang-x86_64-osx10-DA',
                                       'clang-x86_64-osx10-RA',
                                      ],
                         properties = {'revision':WithProperties('%(got_revision)s')})

    gate2 = triggerable.Triggerable(name='phase3',
                         builderNames=['phase3 - tree health',],
                         properties = {'revision':WithProperties('%(got_revision)s')})
    startphase3 = triggerable.Triggerable(name='doPhase3',
                         builderNames=[
                                       'clang-i386-osx10-RA',
                                       'nightly_clang-x86_64-osx10-DA',
                                       'nightly_clang-x86_64-osx10-RA',
                                       'nightly_clang-x86_64-osx10-RA-O0',
                                       'nightly_clang-x86_64-osx10-RA-Os',
                                       'nightly_clang-x86_64-osx10-RA-O3',
                                       'nightly_clang-x86_64-osx10-RA-g',
                                       'nightly_clang-x86_64-osx10-RA-flto',
                                      ],
                         properties = {'revision':WithProperties('%(got_revision)s')})

    gate3 = triggerable.Triggerable(name='phase4',
                         builderNames=['phase4 - validation',],
                         properties = {'revision':WithProperties('%(got_revision)s')})
    startphase4 = triggerable.Triggerable(name='doPhase4',
                         builderNames=[
                                       'clang-x86_64-osx10-RA-stage3',
                                       'nightly_clang-i386-osx10-RA',
                                       'gccTestSuite-clang-x86_64-osx10-RA',
                                       'libcxx-clang-x86_64-osx10-RA',
                                       'boost-trunk-clang-x86_64-osx10-RA',
                                      ],
                         properties = {'revision':WithProperties('%(got_revision)s')})

    LastOne = triggerable.Triggerable(name='GoodBuild',
                         builderNames=['Validated Build',],
                         properties = {'revision':WithProperties('%(got_revision)s')})

    stage3Nightly = triggerable.Triggerable(name='stage3Nightly',
                         builderNames=['nightly_clang-x86_64-osx10-RA-stage3-g',],
                         properties = {'revision':WithProperties('%(got_revision)s')})
    
    
    return [vcScheduler, startphase1, gate1, startphase2, gate2, 
                       startphase3, gate3, startphase4, LastOne, stage3Nightly] 

