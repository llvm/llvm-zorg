# Testing for the Jenkins build.py script
#
# RUN: export TESTING=1
# RUN: export JOB_NAME="FOO"
# RUN: export BUILD_NUMBER=321
# RUN: export BRANCH=master
# Tell build.py to just print commands instead of running.
# RUN: export LLVM_REV=1234
# RUN: mkdir -p %t.SANDBOX/host-compiler/lib %t.SANDBOX/host-compiler/bin %t.SANDBOX/llvm.src %t.SANDBOX/clang.src %t.SANDBOX/libcxx.src %t.SANDBOX/compiler-rt.src %t.SANDBOX/debuginfo-tests.src %t.SANDBOX/clang-tools-extra.src %t.SANDBOX/lldb.src
# RUN: touch %t.SANDBOX/host-compiler/bin/clang
# RUN: python %{src_root}/zorg/jenkins/build.py clang all > %t.log
# RUN: FileCheck --check-prefix CHECK-SIMPLE < %t.log %s
# CHECK-SIMPLE: @@@ Setup debug-info tests @@@
# CHECK-SIMPLE: cd
# CHECK-SIMPLE: 'rm' '-rf' 'llvm/tools/clang/test/debuginfo-tests'
# CHECK-SIMPLE: cd
# CHECK-SIMPLE: 'ln'
# CHECK-SIMPLE: @@@@@@
# CHECK-SIMPLE: @@@ Build Directory @@@
# CHECK-SIMPLE: cd
# CHECK-SIMPLE: 'mkdir' '-p'
# CHECK-SIMPLE: @@@@@@
# CHECK-SIMPLE: @@@ Build Clang @@@
# CHECK-SIMPLE: cd
# CHECK-SIMPLE: 'mkdir' './Build' './Root'
# CHECK-SIMPLE: cd
# CHECK-SIMPLE: '/usr/local/bin/cmake' '-G' 'Ninja' '-C'
# CHECK-SIMPLE: '-DLLVM_ENABLE_ASSERTIONS:BOOL=FALSE'
# CHECK-SIMPLE: '-DCMAKE_BUILD_TYPE=RelWithDebInfo'
# CHECK-SIMPLE: '-DCMAKE_MAKE_PROGRAM=/usr/local/bin/ninja'
# CHECK-SIMPLE: '-DLLVM_VERSION_PATCH=99'
# CHECK-SIMPLE: '-DLLVM_VERSION_SUFFIX=""'
# CHECK-SIMPLE: '-DLLVM_BUILD_EXTERNAL_COMPILER_RT=On'
# CHECK-SIMPLE: '-DCLANG_COMPILER_RT_CMAKE_ARGS
# CHECK-SIMPLE: Apple.cmake'
# CHECK-SIMPLE: '-DCOMPILER_RT_BUILD_SANITIZERS=On'
# CHECK-SIMPLE: '-DCMAKE_INSTALL_PREFIX
# CHECK-SIMPLE: '-DLLVM_REPOSITORY=/foo/workspace/llvm.src'
# CHECK-SIMPLE: '-DCLANG_APPEND_VC_REV=On'
# CHECK-SIMPLE: '-DSVN_REVISION=1234'
# CHECK-SIMPLE: '-DLLVM_BUILD_TESTS=On'
# CHECK-SIMPLE: '-DLLVM_INCLUDE_TESTS=On'
# CHECK-SIMPLE: '-DCLANG_INCLUDE_TESTS=On'
# CHECK-SIMPLE: '-DLLVM_INCLUDE_UTILS=On'
# CHECK-SIMPLE: '-DCMAKE_MACOSX_RPATH=On'
# CHECK-SIMPLE: '-DLLVM_ENABLE_LTO=Off
# CHECK-SIMPLE-NOT: -DLLVM_PARALLEL_LINK_JOBS
# CHECK-SIMPLE: @@@@@@
# CHECK-SIMPLE: @@@ Ninja @@@
# CHECK-SIMPLE: cd
# CHECK-SIMPLE: '/usr/local/bin/ninja' '-v' 'install'
# CHECK-SIMPLE: @@@@@@
# CHECK-SIMPLE: @@@ Tests @@@

# CHECK-SIMPLE: cd
# CHECK-SIMPLE: 'env' 'MALLOC_LOG_FILE=/dev/null' '/usr/local/bin/ninja' '-v' '-k' '0' 'check-all'

# Now Check Assertion Builds have --enable assertions

# RUN: python %{src_root}/zorg/jenkins/build.py clang all --assertions > %t-assert.log
# RUN: FileCheck --check-prefix CHECK-ASSERT < %t-assert.log %s
# CHECK-ASSERT: '/usr/local/bin/cmake' '-G' 'Ninja' '-C'
# CHECK-ASSERT: '-DLLVM_ENABLE_ASSERTIONS:BOOL=TRUE'

# Check LTO

# RUN: python %{src_root}/zorg/jenkins/build.py clang all --lto > %t-lto.log
# RUN: FileCheck --check-prefix CHECK-LTO < %t-lto.log %s
# CHECK-LTO: -DLLVM_PARALLEL_LINK_JOBS
# CHECK-LTO-NOT:: '-DLLVM_ENABLE_LTO=Off

# Now try just a build
# RUN: python %{src_root}/zorg/jenkins/build.py clang build --lto
# RUN: python %{src_root}/zorg/jenkins/build.py clang build

# Just a test
# RUN: python %{src_root}/zorg/jenkins/build.py clang test

# CMake

# RUN: python %{src_root}/zorg/jenkins/build.py cmake all --debug > %t-cmake.log
# RUN: FileCheck --check-prefix CHECK-CMAKE < %t-cmake.log %s
# CHECK-CMAKE: '/usr/local/bin/cmake' '-G' 'Ninja'
# CHECK-CMAKE: -DLLVM_BUILD_EXAMPLES=On
# CHECK-CMAKE: '-DCMAKE_BUILD_TYPE=Debug'
# CHECK-CMAKE: '-DLLVM_ENABLE_ASSERTIONS=Off'
# CHECK-CMAKE: -DLLVM_LIT_ARGS=--xunit-xml-output=testresults.xunit.xml -v --timeout=600
# CHECK-CMAKE: '/usr/local/bin/ninja' '-v' 'all'
# CHECK-CMAKE: '/usr/local/bin/ninja' '-v' '-k' '0' 'check-all'


# RUN: python %{src_root}/zorg/jenkins/build.py cmake build
# RUN: python %{src_root}/zorg/jenkins/build.py cmake test
# RUN: python %{src_root}/zorg/jenkins/build.py cmake testlong

# Derive Functions

# RUN: cd %t.SANDBOX; python %{src_root}/zorg/jenkins/build.py derive > %t-derive.log
# RUN: FileCheck --check-prefix CHECK-DERIVE < %t-derive.log %s
# CHECK-DERIVE: @@@ Derive Source @@@
# CHECK-DERIVE: cd
# CHCEK-DERIVE: Output/test_build.py.tmp.SANDBOX/llvm
# CHECK-DERIVE: 'rsync' '-auvh' '--delete' '--exclude=.svn/' '--exclude=/tools/clang' '--exclude=/projects/libcxx' '--exclude=/tools/clang/tools/extra' '--exclude=/projects/compiler-rt'
# CHECK-DERIVE: /llvm.src/'
# CHECK-DERIVE: test_build.py.tmp.SANDBOX/llvm'
# CHECK-DERIVE: 'rsync' '-auvh' '--delete' '--exclude=.svn/' '--exclude=/tools/clang/tools/extra'
# CHECK-DERIVE: test_build.py.tmp.SANDBOX/clang.src/'
# CHECK-DERIVE: test_build.py.tmp.SANDBOX/llvm/tools/clang'
# CHECK-DERIVE: 'rsync' '-auvh' '--delete' '--exclude=.svn/'
# CHECK-DERIVE: test_build.py.tmp.SANDBOX/libcxx.src/'
# CHECK-DERIVE:test_build.py.tmp.SANDBOX/llvm/projects/libcxx'
# CHECK-DERIVE: 'rsync' '-auvh' '--delete' '--exclude=.svn/'
# CHECK-DERIVE: test_build.py.tmp.SANDBOX/clang-tools-extra.src/'
# CHECK-DERIVE: test_build.py.tmp.SANDBOX/llvm/tools/clang/tools/extra'
# CHECK-DERIVE: 'rsync' '-auvh' '--delete' '--exclude=.svn/'
# CHECK-DERIVE: test_build.py.tmp.SANDBOX/compiler-rt.src/'
# CHECK-DERIVE: test_build.py.tmp.SANDBOX/llvm/projects/compiler-rt'
# CHECK-DERIVE: @@@@@@



# RUN: cd %t.SANDBOX; python %{src_root}/zorg/jenkins/build.py derive-lldb
# RUN: cd %t.SANDBOX; python %{src_root}/zorg/jenkins/build.py derive-llvm+clang
# RUN: cd %t.SANDBOX; python %{src_root}/zorg/jenkins/build.py derive-llvm

# RUN: python %{src_root}/zorg/jenkins/build.py cmake all --lto | FileCheck --check-prefix CHECK-CMAKELTO %s
# CHECK-CMAKELTO: '/usr/local/bin/cmake' '-G' 'Ninja'
# CHECK-CMAKELTO: '-DLLVM_BUILD_EXAMPLES=Off'
# CHECK-CMAKELTO-NOT:: '-DLLVM_ENABLE_LTO=Off
# CHECK-CMAKELTO: '-DLLVM_PARALLEL_LINK_JOBS=1'
# CHECK-CMAKELTO: '-DCMAKE_BUILD_TYPE=Release'
# CHECK-CMAKELTO: '-DSVN_REVISION=1234'

# RUN: env MAX_PARALLEL_LINKS=2 python %{src_root}/zorg/jenkins/build.py cmake all --lto | FileCheck --check-prefix CHECK-CMAKE-PAR-LTO %s
# CHECK-CMAKE-PAR-LTO: '/usr/local/bin/cmake' '-G' 'Ninja'
# CHECK-CMAKE-PAR-LTO: '-DLLVM_BUILD_EXAMPLES=Off'
# CHECK-CMAKE-PAR-LTO-NOT:: '-DLLVM_ENABLE_LTO=Off
# CHECK-CMAKE-PAR-LTO: '-DLLVM_PARALLEL_LINK_JOBS=2'
# CHECK-CMAKE-PAR-LTO: '-DCMAKE_BUILD_TYPE=Release'

# RUN: env MAX_PARALLEL_TESTS=2 python %{src_root}/zorg/jenkins/build.py cmake all | FileCheck --check-prefix CHECK-CMAKE-2-TESTS %s
# CHECK-CMAKE-2-TESTS: '/usr/local/bin/cmake' '-G' 'Ninja'
# CHECK-CMAKE-2-TESTS: '-DLLVM_LIT_ARGS=--xunit-xml-output=testresults.xunit.xml -v --timeout=600 -j 2'

# RUN: python %{src_root}/zorg/jenkins/build.py cmake all --cmake-type=RelWithDebugInfo | FileCheck --check-prefix CHECK-CMAKE-UPLOADS %s
# CHECK-CMAKE-UPLOADS: @@@ Uploading Artifact @@@

# RUN: python %{src_root}/zorg/jenkins/build.py static-analyzer-benchmarks | FileCheck --check-prefix CHECK-STATIC-ANALYZER-BENCHMARKS %s
# CHECK-STATIC-ANALYZER-BENCHMARKS: @@@ Static Analyzer Benchmarks @@@
# CHECK-STATIC-ANALYZER-BENCHMARKS: cd [[WORKSPACE:.*]]/test-suite-ClangAnalyzer/
# CHECK-STATIC-ANALYZER-BENCHMARKS: '[[WORKSPACE]]/utils-analyzer/SATestBuild.py' '--strictness' '0'
# CHECK-STATIC-ANALYZER-BENCHMARKS: @@@@@@

# RUN: python %{src_root}/zorg/jenkins/build.py cmake all --globalisel | FileCheck --check-prefix CHECK-GISEL %s
# CHECK-GISEL: '/usr/local/bin/cmake' '-G' 'Ninja'
# CHECK-GISEL: '-DLLVM_BUILD_GLOBAL_ISEL=ON'

# RUN: python %{src_root}/zorg/jenkins/build.py clang all --lto --cmake-flag="-DFOO" | FileCheck --check-prefix CHECK-CMAKEFLAGS %s
# CHECK-CMAKEFLAGS: '-DFOO'

# Make sure you can pass new build targetss.
# RUN: python %{src_root}/zorg/jenkins/build.py cmake  build --cmake-build-target foo --cmake-build-target bar | FileCheck --check-prefix CHECK-BTARGETS %s
# CHECK-BTARGETS: '/usr/local/bin/ninja' '-v' 'foo' 'bar'

# Make sure you can pass new test targets.
# RUN: python %{src_root}/zorg/jenkins/build.py cmake test --cmake-test-target foo --cmake-test-target bar | FileCheck --check-prefix CHECK-TTARGETS %s
# CHECK-TTARGETS: '/usr/local/bin/ninja' '-v' '-k' '0' 'foo' 'bar'

# Test long should always do check-all, since that is what many bots expect.
# RUN: python %{src_root}/zorg/jenkins/build.py cmake testlong  | FileCheck --check-prefix CHECK-TTARGETS2 %s
# CHECK-TTARGETS2: '/usr/local/bin/ninja' '-v' '-k' '0' 'check-all'
