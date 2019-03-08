set -eux

# Avoid the python in /usr/local/bin.
PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/jbin

if [ -z "HISTORIC_COMPILER" ]; then
    echo "HISTORIC_COMPILER is not set."
    exit 1
fi

if [ -z "WORKSPACE" ]; then
    echo "WORKSPACE is not set."
    exit 1
fi

SRC="$WORKSPACE/src"
BASE_BUILD="$WORKSPACE/lldb-build"
BUILD="$WORKSPACE/lldb-build-${HISTORIC_COMPILER}"
TEST="$WORKSPACE/test-${HISTORIC_COMPILER}"
RESULTS="$WORKSPACE/results-${HISTORIC_COMPILER}"
DEST="$RESULTS/lldb"

LLVM_SRC="$SRC/llvm"
LLDB_SRC="$SRC/llvm/tools/lldb"
TESTCASES_DIR="$LLDB_SRC/test/testcases"
LOGS_DIR="$TEST/logs"
RESULTS_FILE="$TEST/results.xml"

CC="$WORKSPACE/host-compiler/bin/clang"
CXX="$WORKSPACE/host-compiler/bin/clang++"

TOOLS="clang lldb"
PROJECTS=""


echo "@@@ Clean @@@"

CLEAN_DIRS="$TEST $LOGS_DIR $RESULTS $BUILD/lldb-test-build.noindex"

if [ "$CLEAN" = "true" ]; then
  CLEAN_DIRS="$BUILD $CLEAN_DIRS"
fi

for dir in $CLEAN_DIRS; do
  if [ -d $dir ]; then
    rm -rf $dir
  fi
  mkdir -p $dir
done

MODULE_CACHE=$(xcrun clang -fmodules -x c - -o /dev/null '-###' 2>&1 | grep -Eo '\\-fmodules-cache-path=[^"]+' | cut -d'=' -f2)
if [ -d $MODULE_CACHE ]; then
  rm -rf $MODULE_CACHE
fi
rm -rf $BUILD/module.cache

rm -f $WORKSPACE/*.tgz

echo "@@@@@@"

mkdir -p $BUILD
cd $BUILD

echo "@@@ Setup @@@"

{ /usr/local/bin/lldbsign unlock; } 2>/dev/null

echo "@@@@@@"

echo "@@@ Building historical ${HISTORIC_COMPILER} @@@"
function build_clang() {
  CLANG_NAME=$1
  mkdir -p history/$CLANG_NAME
  cd history/$CLANG_NAME
  SVN=/Applications/Xcode.bak/Contents/Developer/usr/bin/svn
  $SVN upgrade $SRC/history/$CLANG_NAME
  $SVN upgrade $SRC/history/$CLANG_NAME/tools/clang
  $SVN upgrade $SRC/history/$CLANG_NAME/projects/libcxx
  cmake $SRC/history/$CLANG_NAME \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLVM_ENABLE_ASSERTIONS=Off \
    -DLLVM_ENABLE_MODULES=On \
    -DLLVM_TARGETS_TO_BUILD='X86' \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_INSTALL_PREFIX="$RESULTS/history/$CLANG_NAME" \
    -G Ninja
  ninja
  cd ../..
}

build_clang $HISTORIC_COMPILER
HISTORIC_CLANG=${BUILD}/history/${HISTORIC_COMPILER}/bin/clang

echo "@@@@@@"

set +x
echo "@@@ Environment for ${HISTORIC_COMPILER} @@@"
env | sort
echo "@@@@@@"
set -eux

python $SCRIPT_PATH/build.py derive-lldb-cmake

echo "@@@ CMake test suite for ${HISTORIC_COMPILER} @@@"
rsync -av --delete $BASE_BUILD/bin $BUILD/
cmake $WORKSPACE/llvm \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLVM_ENABLE_ASSERTIONS=On \
    -DLLVM_ENABLE_MODULES=On \
    -DLLVM_VERSION_PATCH=99 \
    -DLLVM_TARGETS_TO_BUILD='X86' \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_INSTALL_PREFIX="$DEST" \
    -G Ninja \
    -DLLDB_TEST_C_COMPILER="${HISTORIC_CLANG}" \
    -DLLDB_TEST_CXX_COMPILER="${HISTORIC_CLANG}++" \
    -DLLDB_TEST_USER_ARGS="--framework;$BASE_BUILD/bin/LLDB.framework;--executable;$BASE_BUILD/bin/lldb;--skip-category;gmodules;--arch=x86_64;--build-dir;$BUILD;-s=$LOGS_DIR;--env;TERM=vt100;" \
    -DLLVM_LIT_ARGS="--xunit-xml-output=$RESULTS_FILE -v"

echo "@@@@@@"


echo "@@@ Running tests using ${HISTORIC_COMPILER} @@@"
set +e
# FIXME: The LIT tests don't pick the right compiler yet.
env PYTHONPATH=/usr/local/lib/python2.7/site-packages \
    python $BUILD/bin/llvm-lit --xunit-xml-output=$RESULTS_FILE \
        -v $WORKSPACE/llvm/tools/lldb/lit --filter=lldb-Suite --timeout 600
EXIT_STATUS=$?
set -e
echo "@@@@@@"


echo "@@@ Archiving test logs from ${HISTORIC_COMPILER} @@@"
tar zcf "$RESULTS/test_logs.tgz" -C "${LOGS_DIR}" .

if [ $EXIT_STATUS -ne 0 ]; then
    echo "CHECK-LLDB Failed!\n"
    # Exit with zero if only LIT failed.
    # The junit plugin will turn the build yellow.
    # exit 1
fi

# Delete directories that would get deleted first thing by the next build anyway.
rm -rf $BUILD/lldb-test-build.noindex $BUILD/module.cache
