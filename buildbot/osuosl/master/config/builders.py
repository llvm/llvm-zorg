from zorg.buildbot.builders import ClangBuilder, LLVMBuilder, LLVMGCCBuilder

from zorg.buildbot.builders import DragonEggBuilder
reload(DragonEggBuilder)
from zorg.buildbot.builders import DragonEggBuilder

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
{'name' : "llvm-gcc-x86_64-linux-selfhost",
 'slavenames':["osu2"],
 'builddir':"llvm-gcc-x86_64-linux-selfhost",
 'factory':LLVMGCCBuilder.getLLVMGCCBuildFactory(10)}

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
         'factory': ClangBuilder.getClangBuildFactory(clean=False)},
        {'name' : "clang-i686-xp-msvc9",
         'slavenames' :['dunbar-win32-2'],
         'builddir' :"clang-i686-xp-msvc9",
         'factory' : ClangBuilder.getClangMSVCBuildFactory(jobs=2)},
        {'name' : "clang-x86_64-darwin10-selfhost",
         'slavenames' : ["dunbar-darwin10"],
         'builddir' : "clang-x86_64-darwin10-selfhost",
         'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-apple-darwin10',
                                                       useTwoStage=True,
                                                       stage1_config='Release',
                                                       stage2_config='Debug')},
        ]

# Offline.
{'name': "clang-i386-auroraux",
 'slavenames':["evocallaghan"],
 'builddir':"clang-i386-auroraux",
 'factory': ClangBuilder.getClangBuildFactory("i386-pc-auroraux",
                                              jobs="%(jobs)s", make='gmake')},

def _get_experimental_builders():
    return [
        {'name' : "llvm-gcc-x86_64-darwin10-cross-mingw32",
         'slavenames':["kistanova1"],
         'builddir': "llvm-gcc-x86_64-darwin10-cross-mingw32",
         'factory':LLVMGCCBuilder.getLLVMGCCBuildFactory(
                16, build='x86_64-apple-darwin10',
                host='i686-pc-mingw32',
                target='i686-pc-mingw32',
                useTwoStage=False,
                extra_configure_args=['--disable-multilib', '--disable-nls', '--disable-shared',
                                      '--disable-sjlj-exceptions', '--disable-__cxa_atexit',
                                      '--with-local-prefix=/tools'],
                verbose=True,
                env={ 'PATH' : '/cross-tools/bin:/usr/bin:/bin:/usr/sbin:/sbin' },
                ),
         'category':'llvm-gcc'},

        {'name' : "clang-x86_64-darwin10-selfhost-rel",
         'slavenames' : ["dunbar-darwin10"],
         'builddir' : "clang-x86_64-darwin10-selfhost-rel",
         'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-apple-darwin10',
                                                       useTwoStage=True,
                                                       stage1_config='Release',
                                                       stage2_config='Release'),
         'category' : 'clang.exp' },

        {'name' : 'dragonegg-x86_64-linux',
         'slavenames' : ['baldrick16'],
         'builddir' : 'dragonegg-x86_64-linux',
         'factory' : DragonEggBuilder.getBuildFactory(triple='x86_64-pc-linux-gnu'),
         'category' : 'dragonegg.exp' },
        ]

def get_builders():
    for b in _get_llvm_builders():
        b['category'] = 'llvm'
        yield b

    for b in _get_llvmgcc_builders():
        b['category'] = 'llvm-gcc'
        yield b

    for b in _get_clang_builders():
        b['category'] = 'clang'
        yield b

    for b in _get_experimental_builders():
        yield b

# Random other unused builders...

{'name': "clang-x86_64-linux-vg",
 'slavenames':["osu2"],
 'builddir':"clang-x86_64-linux-vg",
 'factory': ClangBuilder.getClangBuildFactory(valgrind=True),
 'category':'clang.exp'}
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
