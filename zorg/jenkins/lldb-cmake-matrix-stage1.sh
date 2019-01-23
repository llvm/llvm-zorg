set -eux

# Avoid the python in /usr/local/bin.
PATH=/usr/bin:/bin:/usr/sbin:/sbin:/usr/local/jbin

if [ -z "WORKSPACE" ]; then
    echo "WORKSPACE is not set."
    exit 1
fi

SRC="$WORKSPACE"
BUILD="$WORKSPACE/lldb-build"
TEST="$WORKSPACE/test"
RESULTS="$WORKSPACE/results"
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

CLEAN_DIRS="$TEST $DEST $LOGS_DIR $RESULTS $BUILD/lldb-test-build.noindex"

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

set +x
echo "@@@ Environment @@@"
env | sort
echo "@@@@@@"
set -eux

python $SCRIPT_PATH/build.py derive-lldb-cmake

echo "@@@ CMake @@@"
cmake $LLVM_SRC \
    -DCMAKE_BUILD_TYPE=Release \
    -DLLVM_ENABLE_ASSERTIONS=On \
    -DLLVM_ENABLE_MODULES=On \
    -DLLVM_VERSION_PATCH=99 \
    -DLLVM_TARGETS_TO_BUILD='X86' \
    -DCMAKE_EXPORT_COMPILE_COMMANDS=ON \
    -DCMAKE_INSTALL_PREFIX="$DEST" \
    -DLLDB_BUILD_FRAMEWORK=On \
    -G Ninja
echo "@@@@@@"

echo "@@@ Compile @@@"
ninja

#python $SCRIPT_PATH/build.py --assertions \
#    --cmake-type=Release \
#   --cmake-flag="-DLLVM_TARGETS_TO_BUILD=X86" \
#    lldb-cmake

echo "@@@@@@"


# Delete directories that would get deleted first thing by the next build anyway.
rm -rf $BUILD/lldb-test-build.noindex $BUILD/module.cache
