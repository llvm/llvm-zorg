from zorg.buildbot.builders import ClangBuilder
reload(ClangBuilder)
from zorg.buildbot.builders import ClangBuilder

from zorg.buildbot.builders import LLVMBuilder
reload(LLVMBuilder)
from zorg.buildbot.builders import LLVMBuilder

from zorg.buildbot.builders import LLVMGCCBuilder
reload(LLVMGCCBuilder)
from zorg.buildbot.builders import LLVMGCCBuilder

from zorg.buildbot.builders import DragonEggBuilder
reload(DragonEggBuilder)
from zorg.buildbot.builders import DragonEggBuilder

from zorg.buildbot.builders import NightlytestBuilder
reload(NightlytestBuilder)
from zorg.buildbot.builders import NightlytestBuilder

from zorg.buildbot.builders import ScriptedBuilder
reload(ScriptedBuilder)
from zorg.buildbot.builders import ScriptedBuilder

from buildbot.steps.source import SVN
from zorg.buildbot.commands.ClangTestCommand import ClangTestCommand

# Plain LLVM builders.
def _get_llvm_builders():
    return [
        {'name': "llvm-i686-linux",
         'slavenames': ["dunbar1"],
         'builddir': "llvm-i686", 
         'factory': LLVMBuilder.getLLVMBuildFactory("i686-pc-linux-gnu", jobs=2, enable_shared=True)},
        {'name': "llvm-x86_64-linux",
         'slavenames': ["osu1"],
         'builddir': "llvm-x86_64",
         'factory': LLVMBuilder.getLLVMBuildFactory(triple="x86_64-pc-linux-gnu")},
        {'name': "llvm-ppc-linux",
         'slavenames':["nick1"],
         'builddir':"llvm-ppc",
         'factory': LLVMBuilder.getLLVMBuildFactory("ppc-linux-gnu", jobs=1, clean=False, timeout=40)},
        {'name': "llvm-arm-linux",
         'slavenames':["ranby1"],
         'builddir':"llvm-arm-linux",
         'factory': LLVMBuilder.getLLVMBuildFactory("arm-pc-linux-gnu", jobs=1, clean=False,
                                                    timeout=40)},
        {'name': "llvm-i686-linux-vg_leak",
         'slavenames':["osu8"],
         'builddir':"llvm-i686-linux-vg_leak",
         'factory': LLVMBuilder.getLLVMBuildFactory("i686-pc-linux-gnu", valgrind=True,
                                                    valgrindLeakCheck=True,
                                                    valgrindSuppressions='utils/valgrind/i386-pc-linux-gnu.supp')},
        {'name': "llvm-x86_64-linux-vg_leak",
         'slavenames':["osu7"],
         'builddir':"llvm-x86_64-linux-vg_leak",
         'factory': LLVMBuilder.getLLVMBuildFactory("x86_64-pc-linux-gnu", valgrind=True,
                                                    valgrindLeakCheck=True,
                                                    valgrindSuppressions='utils/valgrind/x86_64-pc-linux-gnu.supp')},
        ]

# Offline.
{'name': "llvm-alpha-linux",
 'slavenames':["andrew1"],
 'builddir':"llvm-alpha",
 'factory': LLVMBuilder.getLLVMBuildFactory("alpha-linux-gnu", jobs=2)}
{'name': "llvm-i386-auroraux",
 'slavenames':["evocallaghan"],
 'builddir':"llvm-i386-auroraux",
 'factory': LLVMBuilder.getLLVMBuildFactory("i386-pc-auroraux", jobs="%(jobs)s", make='gmake')},

# llvm-gcc self hosting builders.
def _get_llvmgcc_builders():
    return [
        {'name' : "llvm-gcc-i686-darwin10-selfhost",
         'slavenames':["dunbar-darwin10"],
         'builddir':"llvm-gcc-i686-darwin10-selfhost",
         'factory':LLVMGCCBuilder.getLLVMGCCBuildFactory(4, triple='i686-apple-darwin10',
                                                         gxxincludedir='/usr/include/c++/4.2.1')},
        {'name' : "llvm-gcc-x86_64-darwin10-selfhost",
         'slavenames':["dunbar-darwin10"],
         'builddir':"llvm-gcc-x86_64-darwin10-selfhost",
         'factory':LLVMGCCBuilder.getLLVMGCCBuildFactory(4, triple='x86_64-apple-darwin10',
                                                         gxxincludedir='/usr/include/c++/4.2.1')},
        ]

# Offline, no free x86_64 resources.
{'name' : "llvm-x86_64-linux-checks",
 'slavenames':["osu2"],
 'builddir':"llvm-x86_64-linux-checks",
 'factory':LLVMBuilder.getLLVMBuildFactory("x86_64-pc-linux-gnu", jobs=10, expensive_checks=True)}


clang_i386_linux_xfails = [
    'GCCAS.MultiSource/Benchmarks/Prolangs-C/archie-client/archie',
    'GCCAS.MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4',
    'Bytecode.MultiSource/Benchmarks/Prolangs-C/archie-client/archie',
    'Bytecode.MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4',
    'LLC.MultiSource/Applications/oggenc/oggenc',
    'LLC.MultiSource/Benchmarks/Prolangs-C/archie-client/archie',
    'LLC.MultiSource/Benchmarks/VersaBench/bmm/bmm',
    'LLC.MultiSource/Benchmarks/VersaBench/dbms/dbms',
    'LLC.MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4',
    'LLC.SingleSource/Benchmarks/Misc-C++/Large/sphereflake',
    'LLC.SingleSource/Regression/C++/EH/ConditionalExpr',
    'LLC.SingleSource/Regression/C++/EH/function_try_block',
    'LLC.SingleSource/Regression/C++/EH/simple_rethrow',
    'LLC_compile.MultiSource/Applications/oggenc/oggenc',
    'LLC_compile.MultiSource/Benchmarks/Prolangs-C/archie-client/archie',
    'LLC_compile.MultiSource/Benchmarks/VersaBench/bmm/bmm',
    'LLC_compile.MultiSource/Benchmarks/VersaBench/dbms/dbms',
    'LLC_compile.MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4',
    'LLC_compile.SingleSource/Benchmarks/Misc-C++/Large/sphereflake',
    'LLC_compile.SingleSource/Regression/C++/EH/ConditionalExpr',
    'LLC_compile.SingleSource/Regression/C++/EH/function_try_block',
    'LLC_compile.SingleSource/Regression/C++/EH/simple_rethrow',
]

clang_x86_64_linux_xfails = [
    'GCCAS.MultiSource/Benchmarks/Prolangs-C/archie-client/archie',
    'GCCAS.MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4',
    'Bytecode.MultiSource/Benchmarks/Prolangs-C/archie-client/archie',
    'Bytecode.MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4',
    'LLC.MultiSource/Benchmarks/Prolangs-C/archie-client/archie',
    'LLC.MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4',
    'LLC.SingleSource/Regression/C++/EH/ConditionalExpr',
    'LLC.SingleSource/Regression/C++/EH/function_try_block',
    'LLC.SingleSource/Regression/C++/EH/simple_rethrow',
    'LLC.SingleSource/UnitTests/Vector/SSE/sse.expandfft',
    'LLC.SingleSource/UnitTests/Vector/SSE/sse.stepfft',
    'LLC_compile.MultiSource/Benchmarks/Prolangs-C/archie-client/archie',
    'LLC_compile.MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4',
    'LLC_compile.SingleSource/Regression/C++/EH/ConditionalExpr',
    'LLC_compile.SingleSource/Regression/C++/EH/function_try_block',
    'LLC_compile.SingleSource/Regression/C++/EH/simple_rethrow',
    'LLC_compile.SingleSource/UnitTests/2006-12-04-DynAllocAndRestore',
    'LLC_compile.SingleSource/UnitTests/Vector/SSE/sse.expandfft',
    'LLC_compile.SingleSource/UnitTests/Vector/SSE/sse.stepfft',
]

# Clang builders.
def _get_clang_builders():
    return [
        {'name': "clang-x86_64-linux",
         'slavenames':["osu1"],
         'builddir':"clang-x86_64-linux",
         'factory': ClangBuilder.getClangBuildFactory(examples=True)},
        {'name': "clang-i686-linux",
         'slavenames':["dunbar1"],
         'builddir':"clang-i686-linux",
         'factory': ClangBuilder.getClangBuildFactory()},
        {'name' : "clang-i686-darwin10",
         'slavenames' :["dunbar-darwin10"],
         'builddir' :"clang-i686-darwin10",
         'factory': ClangBuilder.getClangBuildFactory(triple='i686-apple-darwin10',
                                                      stage1_config='Release-Asserts')},
        {'name': "clang-i686-freebsd",
         'slavenames':["freebsd1"],
         'builddir':"clang-i686-freebsd",
         'factory': ClangBuilder.getClangBuildFactory(clean=False, use_pty_in_tests=True)},
        {'name' : "clang-i686-xp-msvc9",
         'slavenames' :['dunbar-win32-2'],
         'builddir' :"clang-i686-xp-msvc9",
         'factory' : ClangBuilder.getClangMSVCBuildFactory(jobs=2)},

        {'name': "clang-x86_64-linux-vg",
         'slavenames':["osu7"],
         'builddir':"clang-x86_64-linux-vg",
         'factory': ClangBuilder.getClangBuildFactory(valgrind=True)},

        {'name' : "clang-x86_64-darwin10-selfhost",
         'slavenames' : ["dunbar-darwin10"],
         'builddir' : "clang-x86_64-darwin10-selfhost",
         'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-apple-darwin10',
                                                       useTwoStage=True,
                                                       stage1_config='Release',
                                                       stage2_config='Debug')},

        {'name' : "clang-x86_64-linux-selfhost-rel",
         'slavenames' : ["osu7"],
         'builddir' : "clang-x86_64-linux-selfhost-rel",
         'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-pc-linux-gnu',
                                                       useTwoStage=True,
                                                       stage1_config='Release',
                                                       stage2_config='Release')},

        {'name' : "clang-i686-linux-fnt",
         'slavenames' : ['balint1'],
         'builddir' : "clang-i686-linux-fnt",
         'factory' : NightlytestBuilder.getFastNightlyTestBuildFactory(triple='i686-pc-linux-gnu',
                                                                       stage1_config='Release',
                                                                       test=False,
                                                                       xfails=clang_i386_linux_xfails) },

        {'name' : "clang-x86_64-linux-fnt",
         'slavenames' : ['osu7'],
         'builddir' : "clang-x86_64-linux-fnt",
         'factory' : NightlytestBuilder.getFastNightlyTestBuildFactory(triple='x86_64-pc-linux-gnu',
                                                                       stage1_config='Release',
                                                                       test=False,
                                                                       xfails=clang_x86_64_linux_xfails) },
        ]

# Offline.
{'name': "clang-i386-auroraux",
 'slavenames':["evocallaghan"],
 'builddir':"clang-i386-auroraux",
 'factory': ClangBuilder.getClangBuildFactory("i386-pc-auroraux",
                                              jobs="%(jobs)s", make='gmake')},

def _get_dragonegg_builders():
    return [
        {'name' : 'dragonegg-i386-linux',
         'slavenames' : ['baldrick16'],
         'builddir' : 'dragonegg-i386-linux',
         'factory'   : ScriptedBuilder.getScriptedBuildFactory(
                       source_code  = [SVN(name='svn-llvm',
                                           mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                                           defaultBranch='trunk',
                                           workdir="llvm.src"),
                                       SVN(name='svn-dragonegg',
                                           mode='update', baseURL='http://llvm.org/svn/llvm-project/dragonegg/',
                                           defaultBranch='trunk',
                                           workdir="dragonegg.src"),],
                       launcher     = 'dragonegg.src/extras/buildbot_self_strap-32',),
         'category'  : 'dragonegg'},

        {'name' : 'dragonegg-x86_64-linux',
         'slavenames' : ['baldrick17'],
         'builddir' : 'dragonegg-x86_64-linux',
         'factory'   : ScriptedBuilder.getScriptedBuildFactory(
                       source_code  = [SVN(name='svn-llvm',
                                           mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                                           defaultBranch='trunk',
                                           workdir="llvm.src"),
                                       SVN(name='svn-dragonegg',
                                           mode='update', baseURL='http://llvm.org/svn/llvm-project/dragonegg/',
                                           defaultBranch='trunk',
                                           workdir="dragonegg.src"),],
                       launcher     = 'dragonegg.src/extras/buildbot_self_strap',),
         'category'  : 'dragonegg'},

        ]

def _get_experimental_builders():
    return [

        {'name' : "clang-i386-darwin10-selfhost-rel",
         'slavenames' : ["dunbar-darwin10"],
         'builddir' : "clang-i386-darwin10-selfhost-rel",
         'factory' : ClangBuilder.getClangBuildFactory(triple='i386-apple-darwin10',
                                                       useTwoStage=True,
                                                       stage1_config='Release',
                                                       stage2_config='Release'),
         'category' : 'clang.exp' },
        {'name' : "clang-x86_64-darwin10-selfhost-rel",
         'slavenames' : ["dunbar-darwin10"],
         'builddir' : "clang-x86_64-darwin10-selfhost-rel",
         'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-apple-darwin10',
                                                       useTwoStage=True,
                                                       stage1_config='Release',
                                                       stage2_config='Release'),
         'category' : 'clang.exp' },

        {'name' : "llvm-gcc-x86_64-linux-selfhost",
         'slavenames':["osu7"],
         'builddir':"llvm-gcc-x86_64-linux-selfhost",
         'factory':LLVMGCCBuilder.getLLVMGCCBuildFactory(triple='x86_64-pc-linux-gnu',
                                                         extra_configure_args=['--disable-multilib']),
         'category' : 'llvm-gcc.exp' },

        {'name'      : "llvm-gcc-x86_64-darwin10-self-mingw32",
         'slavenames': [ "kistanova1" ],
         'builddir'  : "llvm-gcc-x86_64-darwin10-self-mingw32",
         'factory'   : ScriptedBuilder.getScriptedBuildFactory(
                       source_code  = [SVN(name='svn-llvm',
                                           mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                                           defaultBranch='trunk',
                                           workdir="llvm.src"),
                                       SVN(name='svn-llvm-gcc',
                                           mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm-gcc-4.2/',
                                           defaultBranch='trunk',
                                           workdir="llvm-gcc.src"),],
                       launcher     = 'llvm-gcc.src/extras/buildbot-launcher',
                       build_script = 'llvm-gcc.src/extras/build-4-mingw32',
                       extra_args   = [],
                       build_steps  = [{'name'          : 'configure_llvm',
                                        'description'   : 'Configure LLVM',
                                        'haltOnFailure' : True },
                                       {'name'          : 'make_llvm',
                                        'description'   : 'Make LLVM',
                                        'extra_args'    : ['-j8'],  # Extra step-specific properties
                                        'haltOnFailure' : True },
                                       {'name'          : 'configure_llvmgcc',
                                        'description'   : 'Configure LLVM-GCC',
                                        'haltOnFailure' : True },
                                       {'name'          : 'make_llvmgcc',
                                        'description'   : 'Make LLVM-GCC',
                                        'haltOnFailure' : True },
                                       {'name'          : 'install_llvmgcc',
                                        'description'   : 'Install LLVM-GCC',
                                        'haltOnFailure' : True },]),
         'category'  : 'llvm-gcc' },

        {'name'      : "llvm-gcc-x86_64-darwin10-cross-mingw32",
         'slavenames': [ "kistanova1" ],
         'builddir'  : "llvm-gcc-x86_64-darwin10-cross-mingw32",
         'factory'   : ScriptedBuilder.getScriptedBuildFactory(
                       source_code  = [SVN(name='svn-llvm',
                                           mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                                           defaultBranch='trunk',
                                           workdir="llvm.src"),
                                       SVN(name='svn-llvm-gcc',
                                           mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm-gcc-4.2/',
                                           defaultBranch='trunk',
                                           workdir="llvm-gcc.src"),],
                       launcher     = 'llvm-gcc.src/extras/buildbot-launcher',
                       build_script = 'llvm-gcc.src/extras/build-x-4-mingw32',
                       extra_args   = [],
                       build_steps  = [{'name'          : 'configure_llvm',
                                        'description'   : 'Configure LLVM',
                                        'haltOnFailure' : True },
                                       {'name'          : 'make_llvm',
                                        'description'   : 'Make LLVM',
                                        'extra_args'    : ['-j8'],  # Extra step-specific properties
                                        'haltOnFailure' : True },
                                       {'name'          : 'test_llvm',
                                        'type'          : ClangTestCommand,
                                        'description'   : 'Test LLVM',
                                        'haltOnFailure' : False },
                                       {'name'          : 'cross_tools',
                                        'description'   : 'Copy cross-tools',
                                        'haltOnFailure' : True },
                                       {'name'          : 'configure_llvmgcc',
                                        'description'   : 'Configure LLVM-GCC',
                                        'haltOnFailure' : True },
                                       {'name'          : 'make_llvmgcc',
                                        'description'   : 'Make LLVM-GCC',
                                        'haltOnFailure' : True },
                                       {'name'          : 'install_llvmgcc',
                                        'description'   : 'Install LLVM-GCC',
                                        'haltOnFailure' : True },]),
         'category'  : 'llvm-gcc' },

        {'name' : "clang-i686-linux-selfhost-rel",
         'slavenames' : ["osu8"],
         'builddir' : "clang-i686-linux-selfhost-rel",
         'factory' : ClangBuilder.getClangBuildFactory(triple='i686-pc-linux-gnu',
                                                       useTwoStage=True,
                                                       stage1_config='Release',
                                                       stage2_config='Release'),
         'category' : 'clang.exp' },

        {'name' : "clang-i686-xp-msvc9_alt",
         'slavenames' :['adobe1'],
         'builddir' :"clang-i686-xp-msvc9_alt",
         'factory' : ClangBuilder.getClangMSVCBuildFactory(jobs=2),
         'category' : 'clang.exp' },

        {'name': "clang-i686-freebsd-selfhost-rel",
         'slavenames':["freebsd1"],
         'builddir':"clang-i686-freebsd-selfhost-rel",
         'factory': ClangBuilder.getClangBuildFactory(triple='i686-pc-freebsd',
                                                      useTwoStage=True,
                                                      stage1_config='Release',
                                                      stage2_config='Release'),
         'category' : 'clang.exp' },

        ]

def get_builders():
    for b in _get_llvm_builders():
        b['category'] = 'llvm'
        yield b

    for b in _get_llvmgcc_builders():
        b['category'] = 'llvm-gcc'
        yield b

    for b in _get_dragonegg_builders():
        b['category'] = 'dragonegg'
        yield b

    for b in _get_clang_builders():
        b['category'] = 'clang'
        yield b
        
    for b in _get_experimental_builders():
        yield b

# Random other unused builders...

{'name': "clang-x86_64-openbsd",
 'slavenames':["ocean1"],
 'builddir':"clang-x86_64-openbsd",
 'factory': ClangBuilder.getClangBuildFactory(),
 'category':'clang.exp'}
{'name': "clang-x86_64-linux-checks",
 'slavenames':["osu2"],
 'builddir':"clang-x86_64-linux-checks",
 'factory': ClangBuilder.getClangBuildFactory(stage1_config='Debug+Checks'),
 'category':'clang.exp'}
