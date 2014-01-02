from zorg.buildbot.builders import ClangBuilder
reload(ClangBuilder)
from zorg.buildbot.builders import ClangBuilder

from zorg.buildbot.builders import LLVMBuilder
reload(LLVMBuilder)
from zorg.buildbot.builders import LLVMBuilder

from zorg.buildbot.builders import LLVMGCCBuilder
reload(LLVMGCCBuilder)
from zorg.buildbot.builders import LLVMGCCBuilder

from zorg.buildbot.builders import LNTBuilder
reload(LNTBuilder)
from zorg.buildbot.builders import LNTBuilder

from zorg.buildbot.builders import DragonEggBuilder
reload(DragonEggBuilder)
from zorg.buildbot.builders import DragonEggBuilder

from zorg.buildbot.builders import NightlytestBuilder
reload(NightlytestBuilder)
from zorg.buildbot.builders import NightlytestBuilder

from zorg.buildbot.builders import ScriptedBuilder
reload(ScriptedBuilder)
from zorg.buildbot.builders import ScriptedBuilder

from zorg.buildbot.builders import PollyBuilder
reload(PollyBuilder)
from zorg.buildbot.builders import PollyBuilder

from zorg.buildbot.builders import LLDBBuilder
reload(LLDBBuilder)
from zorg.buildbot.builders import LLDBBuilder

from zorg.buildbot.builders import LLDBuilder
reload(LLDBBuilder)
from zorg.buildbot.builders import LLDBuilder

from zorg.buildbot.builders import ClangAndLLDBuilder
reload(ClangAndLLDBuilder)
from zorg.buildbot.builders import ClangAndLLDBuilder

from zorg.buildbot.builders import SanitizerBuilder
reload(SanitizerBuilder)
from zorg.buildbot.builders import SanitizerBuilder

from buildbot.steps.source import SVN

# Plain LLVM builders.
def _get_llvm_builders():
    return [
        {'name': "llvm-x86_64-linux",
         'slavenames': ["gcc14"],
         'builddir': "llvm-x86_64",
         'factory': LLVMBuilder.getLLVMBuildFactory(triple="x86_64-pc-linux-gnu")},
        {'name': "llvm-x86_64-ubuntu",
         'slavenames':["arxan_davinci"],
         'builddir':"llvm-x86_64-ubuntu",
         'factory': LLVMBuilder.getLLVMBuildFactory("x86_64-pc-linux-gnu", jobs=4,
                                                    timeout=30)},
        {'name': "llvm-armv5-linux",
         'slavenames':["ranby1"],
         'builddir':"llvm-armv5-linux",
         'factory': LLVMBuilder.getLLVMBuildFactory("armv5-pc-linux-gnu", jobs=1, clean=False,
                                                    timeout=40)},
        {'name': "llvm-ppc64-linux1",
         'slavenames':["chinook"],
         'builddir':"llvm-ppc64",
         'factory': LLVMBuilder.getLLVMBuildFactory("ppc64-linux-gnu", jobs=4, clean=False, timeout=20)},

        {'name': "llvm-s390x-linux1",
         'slavenames':["systemz-1"],
         'builddir':"llvm-s390x-linux1",
         'factory': LLVMBuilder.getLLVMBuildFactory("s390x-linux-gnu", jobs=4, clean=False, timeout=20)},

        {'name': "llvm-x86_64-linux-vg_leak",
         'slavenames':["osu8"],
         'builddir':"llvm-x86_64-linux-vg_leak",
         'factory': LLVMBuilder.getLLVMBuildFactory("x86_64-pc-linux-gnu", valgrind=True,
                                             valgrindLeakCheck=True,
                                             valgrindSuppressions='utils/valgrind/x86_64-pc-linux-gnu.supp')},
        {'name': "llvm-mips-linux",
         'slavenames':["mipsswbrd002"],
         'builddir':"llvm-mips-linux",
         'factory': LLVMBuilder.getLLVMBuildFactory("mips-linux-gnu", timeout=40, config_name='Release+Asserts',
                                                    extra_configure_args=["--with-extra-options=-mips32r2",
                                                                          "--with-extra-ld-options=-mips32r2"])},
        {'name': "llvm-aarch64-linux",
         'slavenames':["aarch64-foundation"],
         'builddir':"llvm-aarch64-linux",
         'factory': LLVMBuilder.getLLVMBuildFactory(config_name='Release+Asserts',
                                                    outOfDir=True,
                                                    extra_configure_args=["--host=aarch64-linux-gnu"])},
        {'name': "llvm-hexagon-elf",
         'slavenames':["hexagon-build-02"],
         'builddir':"llvm-hexagon-elf",
         'factory': LLVMBuilder.getLLVMBuildFactory("hexagon-unknown-elf", timeout=40, config_name='Release+Asserts',
                                                       extra_configure_args=['--build=x86_64-linux-gnu',
                                                                             '--host=x86_64-linux-gnu',
                                                                             '--target=hexagon-unknown-elf',
                                                                             '--enable-targets=hexagon'])},
        ]

# Offline.
{'name': "llvm-alpha-linux",
 'slavenames':["andrew1"],
 'builddir':"llvm-alpha",
 'factory': LLVMBuilder.getLLVMBuildFactory("alpha-linux-gnu", jobs=2)},
{'name': "llvm-i386-auroraux",
 'slavenames':["evocallaghan"],
 'builddir':"llvm-i386-auroraux",
 'factory': LLVMBuilder.getLLVMBuildFactory("i386-pc-auroraux", jobs="%(jobs)s", make='gmake')},
{'name': "llvm-ppc-linux",
 'slavenames':["nick1"],
 'builddir':"llvm-ppc",
 'factory': LLVMBuilder.getLLVMBuildFactory("ppc-linux-gnu", jobs=1, clean=False, timeout=40)},
{'name': "llvm-i686-linux",
 'slavenames': ["dunbar1"],
 'builddir': "llvm-i686",
 'factory': LLVMBuilder.getLLVMBuildFactory("i686-pc-linux-gnu", jobs=2, enable_shared=True)},

# Offline.
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

clang_i386_linux_xfails = [
    'LLC.MultiSource/Applications/oggenc/oggenc',
    'LLC.MultiSource/Benchmarks/VersaBench/bmm/bmm',
    'LLC.MultiSource/Benchmarks/VersaBench/dbms/dbms',
    'LLC.SingleSource/Benchmarks/Misc-C++/Large/sphereflake',
    'LLC.SingleSource/Regression/C++/EH/ConditionalExpr',
    'LLC_compile.MultiSource/Applications/oggenc/oggenc',
    'LLC_compile.MultiSource/Benchmarks/VersaBench/bmm/bmm',
    'LLC_compile.MultiSource/Benchmarks/VersaBench/dbms/dbms',
    'LLC_compile.SingleSource/Benchmarks/Misc-C++/Large/sphereflake',
    'LLC_compile.SingleSource/Regression/C++/EH/ConditionalExpr',
]

clang_x86_64_linux_xfails = [
    'LLC.SingleSource/UnitTests/Vector/SSE/sse.expandfft',
    'LLC.SingleSource/UnitTests/Vector/SSE/sse.stepfft',
    'LLC_compile.SingleSource/UnitTests/Vector/SSE/sse.expandfft',
    'LLC_compile.SingleSource/UnitTests/Vector/SSE/sse.stepfft',
]

# TODO: The following tests marked as expected failures on FreeBSD 9 temporarily.
# Remove after http://llvm.org/bugs/show_bug.cgi?id=18089
# and http://llvm.org/bugs/show_bug.cgi?id=18056 will be fixed and closed.
clang_x86_64_freeBSD9_xfails = [
    'LLC.MultiSource/Benchmarks/SciMark2-C/scimark2',
    'LLC_compile.MultiSource/Benchmarks/SciMark2-C/scimark2',
    'LLC.MultiSource/Benchmarks/nbench/nbench',
    'LLC_compile.MultiSource/Benchmarks/nbench/nbench',
    'LLC.SingleSource/UnitTests/initp1',
    'LLC_compile.SingleSource/UnitTests/initp1',
    'LLC.SingleSource/Benchmarks/Misc/mandel',
    'LLC_compile.SingleSource/Benchmarks/Misc/mandel',
]

polly_x86_64_linux_xfails = [
    'LLC.MultiSource/Applications/sgefa/sgefa',
    'MultiSource/Applications/sgefa/sgefa.execution_time',
    'LLC/MultiSource/Benchmarks/7zip/7zip-benchmark',
    'MultiSource/Benchmarks/7zip/7zip-benchmark.execution_time',
    'LLC_compile/MultiSource/Benchmarks/7zip/7zip-benchmark',
    'MultiSource/Benchmarks/7zip/7zip-benchmark.compile_time',
    'MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4.compile_time',
    'MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4.execution_time',
]

polly_perf_O3_polly_scev_codegen_xfails = [
    'MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4.execution_time',
    'MultiSource/Benchmarks/tramp3d-v4/tramp3d-v4.compile_time',
    'SingleSource/Benchmarks/Misc/oourafft.execution_time',
    'SingleSource/Benchmarks/Misc/oourafft.compile_time',
]

polly_perf_O3_polly_detect_xfails = [
]

# Clang fast builders.
def _get_clang_fast_builders():
    return [
        {'name': "clang-x86_64-debian-fast",
         'slavenames':["gribozavr1"],
         'builddir':"clang-x86_64-debian-fast",
         'factory': ClangBuilder.getClangBuildFactory(
                    env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                         'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes'},
                    stage1_config='Release+Asserts',
                    checkout_compiler_rt=True,
                    outOfDir=True)},

        {'name': "llvm-clang-lld-x86_64-debian-fast",
         'slavenames':["gribozavr1"],
         'builddir':"llvm-clang-lld-x86_64-debian-fast",
         'factory': ClangAndLLDBuilder.getClangAndLLDBuildFactory(
                    env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                         'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes'})},

        {'name': "llvm-clang-lld-x86_64-ubuntu-13.04",
         'slavenames':["gribozavr2"],
         'builddir':"llvm-clang-lld-x86_64-ubuntu-13.04",
         'factory': ClangAndLLDBuilder.getClangAndLLDBuildFactory(
                    env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin',
                         'CC': 'ccache clang', 'CXX': 'ccache clang++', 'CCACHE_CPP2': 'yes'})},

        ]

# Clang builders.
def _get_clang_builders():

    LabPackageCache = 'http://10.1.1.2/packages/'

    return [
        {'name': "clang-x86_64-debian",
         'slavenames':["gcc12"],
         'builddir':"clang-x86_64-debian",
         'factory': ClangBuilder.getClangBuildFactory(extra_configure_args=['--enable-shared'])},

        {'name' : "clang-x86_64-debian-selfhost-rel",
         'slavenames' : ["gcc13"],
         'builddir' : "clang-x86_64-debian-selfhost-rel",
         'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-pc-linux-gnu',
                                                       useTwoStage=True,
                                                       stage1_config='Release+Asserts',
                                                       stage2_config='Release+Asserts')},

        {'name' : "clang-x86_64-debian-fnt",
         'slavenames' : ['gcc20'],
         'builddir' : "clang-x86_64-debian-fnt",
         'factory' : NightlytestBuilder.getFastNightlyTestBuildFactory(triple='x86_64-pc-linux-gnu',
                                                                       stage1_config='Release+Asserts',
                                                                       test=False,
                                                                       xfails=clang_x86_64_linux_xfails)},

        {'name': "clang-atom-d525-fedora-rel",
         'slavenames':["atom1-buildbot"],
         'builddir':"clang-atom-d525-fedora-rel",
         'factory' : ClangBuilder.getClangBuildFactory(stage1_config='Release+Asserts')},

        {'name': "clang-x86_64-ubuntu",
         'slavenames':["arxan_raphael"],
         'builddir':"clang-x86_64-ubuntu",
         'factory' : ClangBuilder.getClangBuildFactory(extra_configure_args=['--enable-shared'])},

        {'name': "clang-native-arm-cortex-a9",
         'slavenames':["as-bldslv1", "as-bldslv2", "as-bldslv3"],
         'builddir':"clang-native-arm-cortex-a9",
         'factory' : ClangBuilder.getClangBuildFactory(
                     stage1_config='Release+Asserts',
                     clean=False,
                     env = { 'CXXFLAGS' : '-Wno-psabi', 'CFLAGS' : '-Wno-psabi'},
                     extra_configure_args=['--build=armv7l-unknown-linux-gnueabihf',
                                           '--host=armv7l-unknown-linux-gnueabihf',
                                           '--target=armv7l-unknown-linux-gnueabihf',
                                           '--with-cpu=cortex-a9',
                                           '--with-fpu=neon',
                                           '--with-float=hard',
                                           '--enable-targets=arm'])},

        {'name': "clang-native-arm-cortex-a15-self-host",
         'slavenames':["linaro-chrome-02"],
         'builddir':"clang-native-arm-cortex-a15-self-host",
         'factory' : ClangBuilder.getClangBuildFactory(
                     stage1_config='Release+Asserts',
                     stage2_config='Release+Asserts',
                     useTwoStage=True,
                     clean=False,
                     test=True,
                     extra_configure_args=[ '--with-cpu=cortex-a15',
                                            '--with-fpu=neon',
                                            '--with-float=hard',
                                            '--enable-targets=arm'])},

        {'name' : "clang-native-arm-lnt",
         'slavenames':["linaro-chrome-01", "linaro-chrome-03"],
         'builddir':"clang-native-arm-lnt",
         'factory' : LNTBuilder.getLNTFactory(triple='armv7l-unknown-linux-gnueabihf',
                                              nt_flags=['--cflag', '-mcpu=cortex-a15', '-j2'],
                                              jobs=2, use_pty_in_tests=True, clean=False,
                                              testerName='LNT-TestOnly-O3', run_cxx_tests=True)},

        {'name': "clang-X86_64-freebsd",
         'slavenames':["as-bldslv6"],
         'builddir':"clang-X86_64-freebsd",
         'factory': NightlytestBuilder.getFastNightlyTestBuildFactory(triple='x86_64-unknown-freebsd8.2',
                                                                       stage1_config='Release+Asserts',
                                                                       test=True)},

        {'name': "clang-native-mingw32-win7",
         'slavenames':["as-bldslv7"],
         'builddir':"clang-native-mingw32-win7",
         'factory' : ClangBuilder.getClangBuildFactory(triple='i686-pc-mingw32',
                                                       useTwoStage=True, test=False,
                                                       stage1_config='Release+Asserts',
                                                       stage2_config='Release+Asserts')},

        {'name' : "clang-ppc64-elf-linux",
         'slavenames' :["chinook-clangslave1"],
         'builddir' :"clang-ppc64-1",
         'factory' : LNTBuilder.getLNTFactory(triple='ppc64-elf-linux1',
                                              nt_flags=['--multisample=3'], jobs=4,  use_pty_in_tests=True,
                                              testerName='O3-plain', run_cxx_tests=True)},

        {'name' : "clang-ppc64-elf-linux2",
         'slavenames' :["chinook-clangslave2"],
         'builddir' :"clang-ppc64-2",
         'factory' : ClangBuilder.getClangBuildFactory(triple='ppc64-elf-linux',
                                                       useTwoStage=True, test=True,
                                                       checkout_compiler_rt=True,
                                                       stage1_config='Release+Asserts',
                                                       stage2_config='Release+Asserts')},

         {'name': "clang-x86_64-linux-vg",
          'slavenames':["osu8"],
          'builddir':"clang-x86_64-linux-vg",
          'factory': ClangBuilder.getClangBuildFactory(valgrind=True)},

         {'name' : "clang-x86_64-linux-selfhost-rel",
          'slavenames' : ["osu8"],
          'builddir' : "clang-x86_64-linux-selfhost-rel",
          'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-pc-linux-gnu',
                                               useTwoStage=True,
                                               stage1_config='Release+Asserts',
                                               stage2_config='Release+Asserts')},

         {'name' : "clang-x86_64-linux-fnt",
          'slavenames' : ['osu8'],
          'builddir' : "clang-x86_64-linux-fnt",
          'factory' : NightlytestBuilder.getFastNightlyTestBuildFactory(triple='x86_64-pc-linux-gnu',
                                                               stage1_config='Release+Asserts',
                                                               test=False,
                                                               xfails=clang_x86_64_linux_xfails)},

         {'name': "clang-mergefunc-x86_64-freeBSD9.2",
          'slavenames':["as-bldslv5"],
         'builddir':"x86_64-freeBSD9.2",
         'factory' : NightlytestBuilder.getFastNightlyTestBuildFactory(triple='x86_64-unknown-freebsd9.2',
                                                               stage1_config='Release+Asserts',
                                                               merge_functions=True,
                                                               make='gmake',
                                                               test=False,
                                                               xfails=clang_x86_64_freeBSD9_xfails)},

        # Clang cross builders.
        {'name' : "clang-x86_64-darwin11-cross-mingw32",
         'slavenames' :["as-bldslv11"],
         'builddir' :"clang-x86_64-darwin11-cross-mingw32",
         'factory' : ClangBuilder.getClangBuildFactory(outOfDir=True, jobs=4,  use_pty_in_tests=True,
                                                       test=False,
                                                       extra_configure_args=['--build=x86_64-apple-darwin11',
                                                                             '--host=x86_64-apple-darwin11',
                                                                             '--target=i686-pc-mingw32'])},

        {'name': "clang-x86_64-darwin11-self-mingw32",
         'slavenames':["as-bldslv11"],
         'builddir':"clang-x86_64-darwin11-self-mingw32",
         'factory' : ClangBuilder.getClangBuildFactory(outOfDir=True, jobs=4, test=False,
                                                       env = { 'PATH' : "/mingw_build_tools/install_with_gcc/bin:/opt/local/bin:/opt/local/sbin:/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/bin:/usr/X11/bin"},
                                                       extra_configure_args=['--build=x86_64-apple-darwin11',
                                                                             '--host=i686-pc-mingw32',
                                                                             '--target=i686-pc-mingw32'])},

        {'name' : "clang-x86_64-darwin11-cross-arm",
         'slavenames' :["as-bldslv11"],
         'builddir' :"clang-x86_64-darwin11-cross-arm",
         'factory' : ClangBuilder.getClangBuildFactory(outOfDir=True, jobs=4,  use_pty_in_tests=True,
                                                       test=False,
                                                       extra_configure_args=['--build=x86_64-apple-darwin11',
                                                                             '--host=x86_64-apple-darwin11',
                                                                             '--target=arm-eabi',
                                                                             '--enable-targets=arm'])},

        {'name' : "clang-x86_64-darwin12-nt-O3",
         'slavenames' :["lab-mini-01"],
         'builddir' :"clang-x86_64-darwin12-nt-O3",
         'factory' : LNTBuilder.getLNTFactory(triple='x86_64-apple-darwin12',
                                              nt_flags=['--multisample=3'], jobs=2,  use_pty_in_tests=True,
                                              testerName='O3-plain', run_cxx_tests=True,
                                              package_cache=LabPackageCache)},

        {'name' : "clang-x86_64-ubuntu-gdb-75",
         'slavenames' :["hpproliant1"],
         'builddir' :"clang-x86_64-ubuntu-gdb-75",
         'factory' : ClangBuilder.getClangBuildFactory(stage1_config='Release+Asserts', run_modern_gdb=True, clean=False)},

        {'name' : "clang-hexagon-elf",
         'slavenames' :["hexagon-build-02"],
         'builddir' :"clang-hexagon-elf",
         'factory' : ClangBuilder.getClangBuildFactory(
                     triple='x86_64-linux-gnu',
                     stage1_config='Release+Asserts',
                     extra_configure_args=['--enable-shared',
                                           '--target=hexagon-unknown-elf',
                                           '--enable-targets=hexagon'])},

        {'name' : "clang-native-arm-cortex-a15-arch",
         'triple' : 'armv7l-unknown-linux-gnueabihf',
         'slavenames' :["mily-odroid-xu-1", "linaro-odroidxu-01"],
         'builddir' :"clang-native-arm-cortex-a15-arch",
         'factory' : ClangBuilder.getClangBuildFactory(
                     stage1_config='Release+Asserts',
                     clean=True,
                     test=True,
                     env = { 'CC' : 'ccache gcc', 'CXX' : 'ccache g++', 'CCACHE_CPP2' : 'yes' },
                     extra_configure_args=[ '--with-cpu=cortex-a15',
                                            '--with-fpu=neon',
                                            '--with-float=hard',
                                            '--enable-targets=arm'])},

        ]

# Offline.
{'name': "clang-native-arm-cortex-a15",
 'slavenames':["linaro-chrome-01"],
 'builddir':"clang-native-arm-cortex-a15",
 'factory' : ClangBuilder.getClangBuildFactory(
             stage1_config='Release+Asserts',
             clean=False,
             env = { 'CXXFLAGS' : '-Wno-psabi', 'CFLAGS' : '-Wno-psabi'},
             extra_configure_args=['--build=armv7l-unknown-linux-gnueabihf',
                                   '--host=armv7l-unknown-linux-gnueabihf',
                                   '--target=armv7l-unknown-linux-gnueabihf',
                                   '--with-cpu=cortex-a15',
                                   '--with-fpu=neon',
                                   '--with-float=hard',
                                   '--enable-targets=arm'])},
{'name': "clang-i386-auroraux",
 'slavenames':["evocallaghan"],
 'builddir':"clang-i386-auroraux",
 'factory': ClangBuilder.getClangBuildFactory("i386-pc-auroraux",
                                              jobs="%(jobs)s", make='gmake')},
{'name': "clang-x86_64-linux",
 'slavenames':["gcc14"],
 'builddir':"clang-x86_64-linux",
 'factory': ClangBuilder.getClangBuildFactory(examples=True)},
{'name': "clang-i686-linux",
 'slavenames':["dunbar1"],
 'builddir':"clang-i686-linux",
 'factory': ClangBuilder.getClangBuildFactory()},
{'name': "clang-arm-linux",
 'slavenames':["nick3"],
 'builddir':"clang-arm-linux",
 'factory': ClangBuilder.getClangBuildFactory()},
{'name' : "clang-i686-darwin10",
 'slavenames' :["dunbar-darwin10"],
 'builddir' :"clang-i686-darwin10",
 'factory': ClangBuilder.getClangBuildFactory(triple='i686-apple-darwin10',
                                              stage1_config='Release')},
{'name' : "clang-i686-xp-msvc9",
 'slavenames' :['dunbar-win32-2'],
 'builddir' :"clang-i686-xp-msvc9",
 'factory' : ClangBuilder.getClangMSVCBuildFactory(jobs=2)},
{'name' : "clang-x86_64-darwin10-selfhost",
 'slavenames' : ["dunbar-darwin10"],
 'builddir' : "clang-x86_64-darwin10-selfhost",
 'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-apple-darwin10',
                                               useTwoStage=True,
                                               stage1_config='Release+Asserts',
                                               stage2_config='Debug+Asserts')},
{'name': "clang-i686-freebsd",
 'slavenames':["freebsd1"],
 'builddir':"clang-i686-freebsd",
 'factory': ClangBuilder.getClangBuildFactory(clean=True, use_pty_in_tests=True)},
{'name' : "clang-i686-linux-fnt",
 'slavenames' : ['balint1'],
 'builddir' : "clang-i686-linux-fnt",
 'factory' : NightlytestBuilder.getFastNightlyTestBuildFactory(triple='i686-pc-linux-gnu',
                                                               stage1_config='Release+Asserts',
                                                               test=False,
                                                               xfails=clang_i386_linux_xfails) },
{'name' : "clang-x86_64-darwin11-cross-linux-gnu",
 'slavenames' :["as-bldslv11"],
 'builddir' :"clang-x86_64-darwin11-cross-linux-gnu",
 'factory' : ClangBuilder.getClangBuildFactory(outOfDir=True, jobs=4,  use_pty_in_tests=True,
                                               run_cxx_tests=True,
                                               extra_configure_args=['--build=x86_64-apple-darwin11',
                                                                     '--host=x86_64-apple-darwin11',
                                                                     '--target=i686-pc-linux-gnu '])},

def _get_dragonegg_builders():
    return [
        {'name' : "dragonegg-x86_64-linux-gcc-4.7-self-host",
         'slavenames' : ["gcc13"],
         'builddir'   : "dragonegg-x86_64-linux-gcc-4.7-self-host",
         'factory'    : DragonEggBuilder.getDragonEggBootstrapFactory(gcc_repository='http://gcc.gnu.org/svn/gcc/branches/gcc-4_7-branch@188917',
                                                                      extra_languages=['fortran', 'objc', 'obj-c++'],
                                                                      extra_gcc_configure_args=['--disable-bootstrap', '--enable-checking',
                                                                                                '--with-mpc=/opt/cfarm/mpc-0.8/'],
                                                                      extra_llvm_configure_args=['--enable-optimized', '--enable-assertions'],
                                                                      env={ 'CFLAGS' : '-march=native' }),
         'category'   : 'dragonegg'},

        {'name' : "dragonegg-i686-linux-gcc-4.6-self-host",
         'slavenames' : ["gcc45"],
         'builddir'   : "dragonegg-i686-linux-gcc-4.6-self-host",
         'factory'    : DragonEggBuilder.getDragonEggBootstrapFactory(gcc_repository='http://gcc.gnu.org/svn/gcc/branches/gcc-4_6-branch@194776',
                                                                      extra_languages=['fortran', 'objc', 'obj-c++'],
                                                                      extra_gcc_configure_args=['--disable-bootstrap', '--enable-checking'],
                                                                      extra_llvm_configure_args=['--enable-optimized', '--enable-assertions'],
                                                                      env={ 'CFLAGS' : '-march=native' }),
         'category'   : 'dragonegg'},

        {'name' : "dragonegg-x86_64-linux-gcc-4.6-self-host",
         'slavenames' : ["gcc15"],
         'builddir'   : "dragonegg-x86_64-linux-gcc-4.6-self-host",
         'factory'    : DragonEggBuilder.getDragonEggBootstrapFactory(gcc_repository='http://gcc.gnu.org/svn/gcc/branches/gcc-4_6-branch@194776',
                                                                      extra_languages=['fortran', 'objc', 'obj-c++'],
                                                                      extra_gcc_configure_args=['--disable-bootstrap', '--enable-checking',
                                                                                                '--with-mpfr=/opt/cfarm/mpfr-2.4.1',
                                                                                                '--with-gmp=/opt/cfarm/gmp-4.2.4',
                                                                                                '--with-mpc=/opt/cfarm/mpc-0.8'],
                                                                      extra_llvm_configure_args=['--enable-optimized', '--enable-assertions'],
                                                                      env={ 'CFLAGS' : '-march=native' }),
         'category'   : 'dragonegg'},

         {'name' : "dragonegg-x86_64-linux-gcc-4.6-self-host-checks",
         'slavenames' : ["gcc10"],
         'builddir'   : "dragonegg-x86_64-linux-gcc-4.6-self-host-checks",
         'factory'    : DragonEggBuilder.getDragonEggBootstrapFactory(gcc_repository='http://gcc.gnu.org/svn/gcc/branches/gcc-4_6-branch@194776',
                                                                      extra_languages=['fortran', 'objc', 'obj-c++'],
                                                                      extra_gcc_configure_args=['--disable-bootstrap', '--enable-checking',
                                                                                                '--with-mpfr=/opt/cfarm/mpfr',
                                                                                                '--with-gmp=/opt/cfarm/gmp',
                                                                                                '--with-mpc=/opt/cfarm/mpc'],
                                                                      extra_llvm_configure_args=['--enable-optimized', '--enable-assertions', '--enable-expensive-checks'],
                                                                      timeout=120),
         'category'   : 'dragonegg'},

        {'name' : "dragonegg-x86_64-linux-gcc-4.6-self-host-release",
         'slavenames' : ["gcc14"],
         'builddir'   : "dragonegg-x86_64-linux-gcc-4.6-self-host-release",
         'factory'    : DragonEggBuilder.getDragonEggBootstrapFactory(gcc_repository='http://gcc.gnu.org/svn/gcc/branches/gcc-4_6-branch@194776',
                                                                      extra_languages=['fortran', 'objc', 'obj-c++'],
                                                                      extra_gcc_configure_args=['--disable-bootstrap', '--enable-checking',
                                                                                                '--with-mpc=/opt/cfarm/mpc-0.8'],
                                                                      extra_llvm_configure_args=['--enable-optimized', '--disable-assertions']),
         'category'   : 'dragonegg'},

        {'name' : "dragonegg-x86_64-linux-gcc-4.6-self-host-debug",
         'slavenames' : ["gcc10"],
         'builddir'   : "dragonegg-x86_64-linux-gcc-4.6-self-host-debug",
         'factory'    : DragonEggBuilder.getDragonEggBootstrapFactory(gcc_repository='http://gcc.gnu.org/svn/gcc/branches/gcc-4_6-branch@194776',
                                                                      extra_languages=['fortran', 'objc', 'obj-c++'],
                                                                      extra_gcc_configure_args=['--disable-bootstrap', '--enable-checking',
                                                                                                '--with-mpfr=/opt/cfarm/mpfr',
                                                                                                '--with-gmp=/opt/cfarm/gmp',
                                                                                                '--with-mpc=/opt/cfarm/mpc'],
                                                                      extra_llvm_configure_args=['--disable-optimized', '--enable-assertions']),
         'category'   : 'dragonegg'},

        {'name' : 'dragonegg-x86_64-linux-gcc-4.6-fnt',
         'slavenames' : ['gcc12'],
         'builddir'   : 'dragonegg-x86_64-linux-gcc-4.6-fnt',
         'factory'    : DragonEggBuilder.getDragonEggNightlyTestBuildFactory(llvm_configure_args=['--enable-optimized', '--enable-assertions'], testsuite_configure_args=['--with-externals=/home/baldrick/externals'], timeout=40),
         'category'   : 'dragonegg'},

        {'name' : 'dragonegg-x86_64-linux-gcc-4.6-test',
         'slavenames' : ['gcc17'],
         'builddir'   : 'dragonegg-x86_64-linux-gcc-4.6-test',
         'factory'    : DragonEggBuilder.getDragonEggTestBuildFactory(
                            gcc='/home/baldrick/local/bin/gcc',
                            svn_testsuites = [
                                              ['http://llvm.org/svn/llvm-project/cfe/trunk/test@158157', 'clang-testsuite'],
                                              ['http://gcc.gnu.org/svn/gcc/branches/gcc-4_6-branch/libjava@194776', 'gcc-libjava'],
                                              ['http://gcc.gnu.org/svn/gcc/branches/gcc-4_6-branch/gcc/testsuite@194776', 'gcc-testsuite'],
                                              ['http://llvm.org/svn/llvm-project/test-suite/trunk@158157', 'llvm-testsuite']
                                             ],
                            llvm_configure_args=['--enable-optimized', '--enable-assertions', '--enable-debug-symbols'],
                            env={'LD_LIBRARY_PATH' : '/home/baldrick/local/lib/gcc/x86_64-unknown-linux-gnu/4.6.3/:/home/baldrick/local/lib64/:/lib64/:/usr/lib64/:/home/baldrick/local/lib:/lib/:/usr/lib/'}
                        ),
         'category'   : 'dragonegg'},

        {'name' : 'dragonegg-i686-linux-gcc-4.5-self-host',
         'slavenames' : ['gcc16'],
         'builddir'   : 'dragonegg-i686-linux-gcc-4.5-self-host',
         'factory'    : DragonEggBuilder.getDragonEggBootstrapFactory(gcc_repository='http://gcc.gnu.org/svn/gcc/branches/gcc-4_5-branch@188355',
                                                                      extra_languages=['fortran', 'objc', 'obj-c++'],
                                                                      extra_gcc_configure_args=['--disable-bootstrap', '--disable-multilib', '--enable-checking',
                                                                                                '--build=i686-pc-linux-gnu', '--enable-targets=all',
                                                                                                '--with-mpfr=/home/baldrick/cfarm-32',
                                                                                                '--with-gmp=/home/baldrick/cfarm-32',
                                                                                                '--with-mpc=/home/baldrick/cfarm-32',
                                                                                                '--with-libelf=/home/baldrick/cfarm-32'],
                                                                      extra_llvm_configure_args=['--enable-optimized', '--enable-assertions',
                                                                                                 '--build=i686-pc-linux-gnu'],
                                                                      env={'CC' : 'gcc -m32', 'CXX' : 'g++ -m32',
                                                                           'LD_LIBRARY_PATH' : '/home/baldrick/cfarm-32/lib',
                                                                           'CPPFLAGS' : '-I/home/baldrick/cfarm-32/include'}),
         'category'   : 'dragonegg'},

        {'name' : 'dragonegg-x86_64-linux-gcc-4.5-self-host',
         'slavenames' : ['gcc16'],
         'builddir'   : 'dragonegg-x86_64-linux-gcc-4.5-self-host',
         'factory'    : DragonEggBuilder.getDragonEggBootstrapFactory(gcc_repository='http://gcc.gnu.org/svn/gcc/branches/gcc-4_5-branch@188355',
                                                                      extra_languages=['fortran', 'objc', 'obj-c++'],
                                                                      extra_gcc_configure_args=['--disable-bootstrap', '--disable-multilib', '--enable-checking', '--with-mpfr=/opt/cfarm/mpfr', '--with-gmp=/opt/cfarm/gmp', '--with-mpc=/opt/cfarm/mpc', '--with-libelf=/opt/cfarm/libelf-0.8.12'],
                                                                      extra_llvm_configure_args=['--enable-optimized', '--enable-assertions'],
                                                                      env={'CPPFLAGS' : '-I/opt/cfarm/mpfr/include -I/opt/cfarm/gmp/include/ -I/opt/cfarm/mpc/include/'}),
         'category'   : 'dragonegg'},

        ]

# Polly builders.
def _get_polly_builders():
    return [
        {'name': "polly-amd64-linux",
         'slavenames':["grosser1"],
         'builddir':"polly-amd64-linux",
         'factory': PollyBuilder.getPollyBuildFactory()},

#        Disabled, as it is unavailable since several weeks.
#        {'name': "polly-intel32-linux",
#         'slavenames':["botether"],
#         'builddir':"polly-intel32-linux",
#         'factory': PollyBuilder.getPollyBuildFactory()},

        {'name': "polly-perf-O3",
         'slavenames':["pollyperf2", "pollyperf3", "pollyperf4", "pollyperf5"],
         'builddir':"pollyperf-O3",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=10'],
                                                    reportBuildslave=False,
                                                    testerName='pollyperf-O3')},
        {'name': "polly-perf-O3-polly",
         'slavenames':["pollyperf6"],
         'builddir':"pollyperf-O3-polly",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=10', '--mllvm=-polly'],
                                                    xfails=polly_x86_64_linux_xfails,
                                                    reportBuildslave=False,
                                                    testerName='pollyperf-O3-polly')},
        {'name': "polly-perf-O3-polly-codegen-isl",
         'slavenames':["pollyperf7"],
         'builddir':"pollyperf-O3-polly-codegen-isl",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=10', '--mllvm=-polly', '--mllvm=-polly-code-generator=isl'],
                                                    xfails=polly_x86_64_linux_xfails,
                                                    reportBuildslave=False,
                                                    testerName='pollyperf-O3-polly-codegen-isl')},
        {'name': "polly-perf-O3-polly-scev",
         'slavenames':["pollyperf10"],
         'builddir':"pollyperf-O3-polly-scev",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=10', '--mllvm=-polly', '--mllvm=-polly-codegen-scev'],
                                                    xfails=polly_perf_O3_polly_scev_codegen_xfails,
                                                    reportBuildslave=False,
                                                    testerName='pollyperf-O3-polly-scev')},
        {'name': "polly-perf-O3-polly-scev-codegen-isl",
         'slavenames':["pollyperf11"],
         'builddir':"pollyperf-O3-polly-svev-codegen-isl",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=10', '--mllvm=-polly', '--mllvm=-polly-code-generator=isl', '--mllvm=-polly-codegen-scev'],
                                                    xfails=polly_perf_O3_polly_scev_codegen_xfails,
                                                    reportBuildslave=False,
                                                    testerName='pollyperf-O3-polly-scev-codegen-isl')},
        {'name': "polly-perf-O3-polly-detect",
         'slavenames':["pollyperf14"],
         'builddir':"pollyperf-O3-polly-detect",
         'factory': PollyBuilder.getPollyLNTFactory(triple="x86_64-pc-linux-gnu",
                                                    nt_flags=['--multisample=10', '--mllvm=-polly', '--mllvm=-polly-code-generator=none', '--mllvm=-polly-optimizer=none'],
                                                    xfails=polly_perf_O3_polly_detect_xfails,
                                                    reportBuildslave=False,
                                                    testerName='pollyperf-O3-polly-detect')}
       ]

# LLDB builders.
def _get_lldb_builders():

#   gcc_m32_latest_env = gcc_latest_env.copy()
#   gcc_m32_latest_env['CC'] += ' -m32'
#   gcc_m32_latest_env['CXX'] += ' -m32'
#
    return [
        {'name': "lldb-x86_64-debian-clang",
         'slavenames': ["gribozavr1"],
         'builddir': "lldb-x86_64-clang",
         'factory': LLDBBuilder.getLLDBBuildFactory(triple=None, # use default
                                                    extra_configure_args=['--enable-cxx11', '--enable-optimized', '--enable-assertions'],
                                                    env={'PATH':'/home/llvmbb/bin/clang-latest/bin:/home/llvmbb/bin:/usr/local/bin:/usr/local/bin:/usr/bin:/bin:/usr/local/games:/usr/games'})},
        {'name': "lldb-x86_64-linux",
         'slavenames': ["gcc20"],
         'builddir': "lldb-x86_64",
         'factory': LLDBBuilder.getLLDBBuildFactory(triple="x86_64-pc-linux-gnu",
                                                    env={'CXXFLAGS' : '-std=c++0x'})},
        {'name': "lldb-x86_64-darwin12",
         'slavenames': ["lab-mini-02"],
         'builddir': "build.lldb-x86_64-darwin12",
         'factory': LLDBBuilder.getLLDBxcodebuildFactory()},
#       {'name': "lldb-i686-debian",
#        'slavenames': ["gcc15"],
#        'builddir': "lldb-i686-debian",
#        'factory': LLDBBuilder.getLLDBBuildFactory(triple="i686-pc-linux-gnu",
#                                                   env=gcc_m32_latest_env)}
       ]

# LLD builders.
def _get_lld_builders():
    return [
        {'name': "lld-x86_64-darwin11",
         'slavenames' :["as-bldslv11"],
         'builddir':"lld-x86_64-darwin11",
         'factory': LLDBuilder.getLLDBuildFactory(clean=False),
         'category'   : 'lld'},

        {'name': "lld-x86_64-win7",
         'slavenames' :["as-bldslv4"],
         'builddir':"lld-x86_64-win7",
         'factory': LLDBuilder.getLLDWinBuildFactory(clean=False),
         'category'   : 'lld'},

        {'name': "lld-x86_64-freeBSD",
         'slavenames' :["as-bldslv5"],
         'builddir':"lld-x86_64-freeBSD",
         'factory': LLDBuilder.getLLDBuildFactory(jobs=32),
         'category'   : 'lld'},

        {'name': "lld-powerpc-linux-debian",
         'slavenames' :["mily-mini-1"],
         'builddir': "lld-powerpc-linux-debian",
         'factory': LLDBuilder.getLLDBuildFactory(clean=True,
                                                  jobs=2, 
                                                  env={ 
                                                      'CC' : 'ccache gcc-4.8', 
                                                      'CXX': 'ccache g++-4.8',
                                                      'CCACHE_CPP2' : 'yes',
                                                      'LD' : 'ld.gold'}),
          'category' : 'lld'},
         ]

# Sanitizer builders.
def _get_sanitizer_builders():
      return [
          {'name': "sanitizer-x86_64-linux",
           'slavenames' :["sanitizer-buildbot1"],
           'builddir': "sanitizer-x86_64-linux",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},

          {'name': "sanitizer-x86_64-linux-bootstrap",
           'slavenames' :["sanitizer-buildbot2"],
           'builddir': "sanitizer-x86_64-linux-bootstrap",
           'factory': SanitizerBuilder.getSanitizerBuildFactory()},

          # hexagon-build-03: /opt/usr/bin contains clang-3.4 for sanitizer.
          {'name': "llvm-clang-lld-x86_64-ubuntu-13.04-sanitize-address",
           'slavenames':["hexagon-build-03"],
           'builddir':"llvm-clang-lld-x86_64-ubuntu-13.04-fsanitize-address",
           'factory': ClangAndLLDBuilder.getClangAndLLDBuildFactory(
                                             buildWithSanitizerOptions=['-fsanitize=address'],
                                             env={'PATH':'/opt/usr/bin:/usr/local/bin:/usr/bin:/bin'})},
          ]

# Experimental and stopped builders
def _get_experimental_builders():
    return [
        {'name': "llvm-ppc64-linux2",
         'slavenames':["coho"],
         'builddir':"llvm-ppc64-2",
         'factory': LLVMBuilder.getLLVMBuildFactory("ppc64-linux-gnu", jobs=4, clean=False, timeout=20),
         'category' : 'llvm'},

        {'name': "clang-atom-d525-fedora",
         'slavenames':["atom-buildbot"],
         'builddir':"clang-atom-d525-fedora",
         'factory' : ClangBuilder.getClangBuildFactory(extra_configure_args=['--enable-shared']),
         'category' : 'clang'},

        {'name': "clang-amd64-openbsd",
         'slavenames':["openbsd-buildslave"],
         'builddir':"clang-openbsd",
         'factory' : ClangBuilder.getClangBuildFactory(stage1_config='Release+Asserts'),
         'category' : 'clang'},
        ]

def get_builders():
    for b in _get_llvm_builders():
        b['category'] = 'llvm'
        yield b

    for b in _get_dragonegg_builders():
        b['category'] = 'dragonegg'
        yield b

    for b in _get_clang_fast_builders():
        b['category'] = 'clang_fast'
        yield b

    for b in _get_clang_builders():
        b['category'] = 'clang'
        yield b

    for b in _get_polly_builders():
        b['category'] = 'polly'
        yield b

    for b in _get_lld_builders():
        b['category'] = 'lld'
        yield b

    for b in _get_lldb_builders():
        b['category'] = 'lldb'
        yield b

    for b in _get_sanitizer_builders():
        b['category'] = 'sanitizer'
        yield b

    for b in _get_experimental_builders():
        yield b

# Random other unused builders...
{'name': "clang-x86_64-openbsd",
 'slavenames':["ocean1"],
 'builddir':"clang-x86_64-openbsd",
 'factory': ClangBuilder.getClangBuildFactory(),
 'category':'clang.exp'},
{'name': "clang-x86_64-linux-checks",
 'slavenames':["osu2"],
 'builddir':"clang-x86_64-linux-checks",
 'factory': ClangBuilder.getClangBuildFactory(stage1_config='Debug+Asserts+Checks'),
 'category':'clang.exp'},
{'name' : "clang-i386-darwin10-selfhost-rel",
 'slavenames' : ["dunbar-darwin10"],
 'builddir' : "clang-i386-darwin10-selfhost-rel",
 'factory' : ClangBuilder.getClangBuildFactory(triple='i386-apple-darwin10',
                                               useTwoStage=True,
                                               stage1_config='Release+Asserts',
                                               stage2_config='Release+Asserts'),
 'category' : 'clang.exp' },
{'name' : "clang-x86_64-darwin10-selfhost-rel",
 'slavenames' : ["dunbar-darwin10"],
 'builddir' : "clang-x86_64-darwin10-selfhost-rel",
 'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-apple-darwin10',
                                               useTwoStage=True,
                                               stage1_config='Release+Asserts',
                                               stage2_config='Release+Asserts'),
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
                                              stage1_config='Release+Asserts',
                                              stage2_config='Release+Asserts'),
 'category' : 'clang.exp' },
{'name': "llvm-x86_64-debian-debug-werror",
 'slavenames':["obbligato-ellington"],
 'builddir':"llvm-x86-64-debian-debug-werror",
 'factory': LLVMBuilder.getLLVMBuildFactory("x86_64-pc-linux-gnu",
                                            config_name='Debug+Asserts',
                                            extra_configure_args=["--enable-werror"]),
 'category' : 'llvm'},
{'name': "llvm-x86_64-debian-release-werror",
 'slavenames':["obbligato-ellington"],
 'builddir':"llvm-x86-64-debian-release-werror",
 'factory': LLVMBuilder.getLLVMBuildFactory("x86_64-pc-linux-gnu",
                                            config_name='Release+Asserts',
                                            extra_configure_args=["--enable-werror"]),
 'category' : 'llvm'},
{'name': "clang-x86_64-debian-debug-werror",
 'slavenames':["obbligato-ellington"],
 'builddir':"clang-x86-64-debian-debug-werror",
 'factory': ClangBuilder.getClangBuildFactory(triple="x86_64-pc-linux-gnu",
                                             useTwoStage=True,
                                             stage1_config='Debug+Asserts',
                                             stage2_config='Debug+Asserts',
                                             extra_configure_args=["--enable-werror"]),
 'category' : 'clang'},
# Cortex-A9 check-all self-host
{'name': "clang-native-arm-cortex-a9-self-host",
 'slavenames':["linaro-panda-02"],
 'builddir':"clang-native-arm-cortex-a9-self-host",
 'factory' : ClangBuilder.getClangBuildFactory(
             stage1_config='Release+Asserts',
             stage2_config='Release+Asserts',
             useTwoStage=True,
             clean=False,
             test=True,
             extra_configure_args=[ '--with-cpu=cortex-a9',
                                    '--with-fpu=neon',
                                    '--with-float=hard',
                                    '--enable-targets=arm']),
 'category' : 'clang'},
{'name': "clang-x86_64-debian-release-werror",
 'slavenames':["obbligato-ellington"],
 'builddir':"clang-x86-64-debian-release-werror",
 'factory': ClangBuilder.getClangBuildFactory(triple="x86_64-pc-linux-gnu",
                                             useTwoStage=True,
                                             stage1_config='Release+Asserts',
                                             stage2_config='Release+Asserts',
                                             extra_configure_args=["--enable-werror"]),
 'category' : 'clang'},
{'name': "clang-native-mingw64-win7",
 'slavenames':["sschiffli1"],
 'builddir':"clang-native-mingw64-win7",
 'factory' : ClangBuilder.getClangMinGWBuildFactory(),
 'category' : 'clang'},
LabPackageCache = 'http://10.1.1.2/packages/'
{'name' : "clang-x86_64-darwin12-nt-O3-vectorize",
 'slavenames' :["lab-mini-03"],
 'builddir' :"clang-x86_64-darwin12-nt-O3-vectorize",
 'factory' : LNTBuilder.getLNTFactory(triple='x86_64-apple-darwin12',
                                      nt_flags=['--mllvm=-vectorize', '--multisample=3'], jobs=2,
                                      use_pty_in_tests=True, testerName='O3-vectorize',
                                      run_cxx_tests=True, package_cache=LabPackageCache),
 'category' : 'clang'},
{'name' : "clang-x86_64-darwin10-nt-O0-g",
 'slavenames' :["lab-mini-03"],
 'builddir' :"clang-x86_64-darwin10-nt-O0-g",
 'factory' : LNTBuilder.getLNTFactory(triple='x86_64-apple-darwin10',
                                      nt_flags=['--multisample=3', 
                                                '--optimize-option',
                                                '-O0', '--cflag', '-g'],
                                      jobs=2,  use_pty_in_tests=True,
                                      testerName='O0-g', run_cxx_tests=True,
                                      package_cache=LabPackageCache),
 'category' : 'clang'},
{'name' : "clang-x86_64-darwin12-gdb",
 'slavenames' :["lab-mini-04"],
 'builddir' :"clang-x86_64-darwin12-gdb",
 'factory' : ClangBuilder.getClangBuildFactory(triple='x86_64-apple-darwin12', stage1_config='Release+Asserts', run_gdb=True),
 'category' : 'clang'},
{'name': "llvm-ppc-darwin",
 'slavenames':["arxan_bellini"],
 'builddir':"llvm-ppc-darwin",
 'factory': LLVMBuilder.getLLVMBuildFactory("ppc-darwin", jobs=2, clean=True,
                    config_name = 'Release',
                    env = { 'CC' : "/usr/bin/gcc-4.2",
                            'CXX': "/usr/bin/g++-4.2" },
                    extra_configure_args=['--enable-shared'],
                    timeout=600),
 'category' : 'llvm'},
