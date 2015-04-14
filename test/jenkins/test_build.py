# Testing for the Jenkins build.py script
#
# RUN: export TESTING=1
# RUN: export JOB_NAME="FOO"
# RUN: export BUILD_NUMBER=321
# Tell build.py to just print commands instead of running.
# RUN: export LLVM_REV=1234
# RUN: mkdir -p %t.SANDBOX/host-compiler/lib %t.SANDBOX/host-compiler/bin %t.SANDBOX/llvm.src %t.SANDBOX/clang.src %t.SANDBOX/libcxx.src %t.SANDBOX/compiler-rt.src %t.SANDBOX/debuginfo-tests.src %t.SANDBOX/clang-tools-extra.src %t.SANDBOX/lldb.src
# RUN: touch %t.SANDBOX/host-compiler/bin/clang
# RUN: python %{src_root}/zorg/jenkins/build.py clang all > %t.log
# RUN: FileCheck --check-prefix CHECK-SIMPLE < %t.log %s
# CHECK-SIMPLE: @@@ Configure @@@
# CHECK-SIMPLE: cd
# CHECK-SIMPLE: configure' '--disable-assertions' '--enable-optimized' '--disable-bindings' '--enable-targets=x86,x86_64,arm,aarch64' '--prefix=/
# CHECK-SIMPLE: @@@@@@
# CHECK-SIMPLE: @@@ Make All @@@
# CHECK-SIMPLE: 'make' '-j' '4' 'VERBOSE=1' 'CLANG_REPOSITORY_STRING=FOO' 'SVN_REVISION=1234' 'LLVM_VERSION_INFO= (FOO: trunk 1234)'
# CHECK-SIMPLE: @@@@@@
# CHECK-SIMPLE: @@@ Make Install @@@
# CHECK-SIMPLE: 'make' 'install-clang' '-j' '4'
# CHECK-SIMPLE: @@@@@@
# CHECK-SIMPLE: @@@ Upload artifact @@@
# CHECK-SIMPLE: 'tar' 'zcvf' '../clang-r1234-tNONE-b321.tar.gz' '.'
# CHECK-SIMPLE: cd
# CHECK-SIMPLE: 'scp' 'clang-r1234-tNONE-b321.tar.gz' 'buildslave@labmaster2.local:/Library/WebServer/Documents/artifacts/FOO/'
# CHECK-SIMPLE: cd
# CHECK-SIMPLE: 'scp' 'last_good_build.properties' 'buildslave@labmaster2.local:/Library/WebServer/Documents/artifacts/FOO/'
# CHECK-SIMPLE: cd
# CHECK-SIMPLE: 'ssh' 'buildslave@labmaster2.local' 'ln' '-fs' '/Library/WebServer/Documents/artifacts/FOO/clang-r1234-tNONE-b321.tar.gz' '/Library/WebServer/Documents/artifacts/FOO/latest'
# CHECK-SIMPLE: @@@@@@
# CHECK-SIMPLE: @@@ Make Check @@@
# CHECK-SIMPLE: cd
# CHECK-SIMPLE: 'make' 'VERBOSE=1' 'check-all' 'LIT_ARGS=--xunit-xml-output=testresults.xunit.xml -v'
# CHECK-SIMPLE: @@@@@@

# Now Check Assertion Buiilds have --enable assertions


# RUN: python %{src_root}/zorg/jenkins/build.py clang all --assertions > %t-assert.log
# RUN: FileCheck --check-prefix CHECK-ASSERT < %t-assert.log %s
# CHECK-ASSERT: configure' '--enable-assertions' '--enable-optimized' '--disable-bindings' '--enable-targets=x86,x86_64,arm,aarch64' '--prefix=
# CHECK-ASSERT: clang-install' '--enable-libcpp'
# CHECK-ASSERT: 'make' '-j' '4' 'VERBOSE=1' 'CLANG_REPOSITORY_STRING=FOO' 'SVN_REVISION=1234' 'LLVM_VERSION_INFO= (FOO: trunk 1234)'
# CHECK-ASSERT: 'make' 'install-clang' '-j' '4'
# CHECK-ASSERT: 'make' 'VERBOSE=1' 'check-all' 'LIT_ARGS=--xunit-xml-output=testresults.xunit.xml -v'


# Check LTO

# RUN: python %{src_root}/zorg/jenkins/build.py clang all --lto > %t-lto.log
# RUN: FileCheck --check-prefix CHECK-LTO < %t-lto.log %s
# CHECK-LTO: configure' '--disable-assertions' '--with-extra-options=-flto -gline-tables-only' '--enable-optimized' '--disable-bindings' '--enable-targets=x86,x86_64,arm,aarch64' '--prefix=
# CHECK-LTO: clang-install' '--enable-libcpp'
# CHECK-LTO: 'make' '-j' '4' 'VERBOSE=1' 'CLANG_REPOSITORY_STRING=FOO' 'SVN_REVISION=1234' 'LLVM_VERSION_INFO= (FOO: trunk 1234)'
# CHECK-LTO: 'make' 'install-clang' '-j' '4'
# CHECK-LTO: 'make' 'VERBOSE=1' 'check-all' 'LIT_ARGS=--xunit-xml-output=testresults.xunit.xml -v'


# Now try just a build
# RUN: python %{src_root}/zorg/jenkins/build.py clang build --lto
# RUN: python %{src_root}/zorg/jenkins/build.py clang build

# Just a test
# RUN: python %{src_root}/zorg/jenkins/build.py clang test

# CMake

# RUN: python %{src_root}/zorg/jenkins/build.py cmake all --debug > %t-cmake.log
# RUN: FileCheck --check-prefix CHECK-CMAKE < %t-cmake.log %s
# CHECK-CMAKE: '/usr/local/bin/cmake' '-G' 'Ninja'
# CHECK-CMAKE: '-DCMAKE_BUILD_TYPE=Debug'
# CHECK-CMAKE: '-DLLVM_ENABLE_ASSERTIONS=Off'
# CHECK-CMAKE: -DLLVM_LIT_ARGS=--xunit-xml-output=testresults.xunit.xml -v
# CHECK-CMAKE: -DLLVM_BUILD_EXAMPLES=On
# CHECK-CMAKE: '/usr/local/bin/ninja'
# CHECK-CMAKE: '/usr/local/bin/ninja' 'check' 'check-clang'
# CHECK-CMAKE: '/usr/local/bin/ninja' 'check-all'


# RUN: python %{src_root}/zorg/jenkins/build.py cmake build
# RUN: python %{src_root}/zorg/jenkins/build.py cmake test
# RUN: python %{src_root}/zorg/jenkins/build.py cmake testlong

# Derive Functions

# RUN: cd %t.SANDBOX; python %{src_root}/zorg/jenkins/build.py derive > %t-derive.log
# RUN: FileCheck --check-prefix CHECK-DERIVE < %t-derive.log %s
# CHECK-DERIVE: @@@ Derive Source @@@
# CHECK-DERIVE: cd
# CHCEK-DERIVE: Output/test_build.py.tmp.SANDBOX/llvm
# CHECK-DERIVE: 'rsync' '-auvh' '--delete' '--exclude=.svn/' '--exclude=/tools/clang' '--exclude=/projects/libcxx' '--exclude=/tools/clang/tools/extra' '--exclude=/projects/compiler-rt' '--exclude=/tools/clang/test/debuginfo-tests'
# CHECK-DERIVE: /llvm.src/'
# CHECK-DERIVE: test_build.py.tmp.SANDBOX/llvm'
# CHECK-DERIVE: 'rsync' '-auvh' '--delete' '--exclude=.svn/' '--exclude=/tools/clang/tools/extra' '--exclude=/tools/clang/test/debuginfo-tests'
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
# CHECK-DERIVE: 'rsync' '-auvh' '--delete' '--exclude=.svn/'
# CHECK-DERIVE: test_build.py.tmp.SANDBOX/debuginfo-tests.src/'
# CHECK-DERIVE: test_build.py.tmp.SANDBOX/llvm/tools/clang/test/debuginfo-tests'
# CHECK-DERIVE: @@@@@@



# RUN: cd %t.SANDBOX; python %{src_root}/zorg/jenkins/build.py derive-lldb
# RUN: cd %t.SANDBOX; python %{src_root}/zorg/jenkins/build.py derive-llvm+clang
# RUN: cd %t.SANDBOX; python %{src_root}/zorg/jenkins/build.py derive-llvm

# RUN: python %{src_root}/zorg/jenkins/build.py cmake all --lto > %t-cmake-lto.log
# RUN: FileCheck --check-prefix CHECK-CMAKE < %t-cmake.log %s
# CHECK-CMAKELTO: '/usr/local/bin/cmake' '-G' 'Ninja'
# CHECK-CMAKELTO: '-DCMAKE_C_FLAGS=-flto' '-DCMAKE_CXX_FLAGS=-flto'
# CHECK-CMAKELTO: '-DLLVM_PARALLEL_LINK_JOBS=1'
# CHECK-CMAKELTO: '-DCMAKE_BUILD_TYPE=Release'

# RUN: python %{src_root}/zorg/jenkins/build.py cmake all --cmake-type=RelWithDebugInfo
