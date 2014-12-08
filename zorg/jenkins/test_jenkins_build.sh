#!/bin/bash
# This is a simple tester for the Jenkins build.py.  Use at your own risk, it modifies the local src dir.
# This should be replaced with a real tester.

set -u
set -e

# Tell build.py to just print commands instead of running.
export TESTING=1

export LLVM_REV=1234


# Some stub files.
rm -rf host-compiler
mkdir -p host-compiler/lib
mkdir -p host-compiler/bin
touch host-compiler/bin/clang
mkdir -p llvm.src
mkdir -p clang.src
mkdir -p libcxx.src
mkdir -p compiler-rt.src
mkdir -p debuginfo-tests.src
mkdir -p clang-tools-extra.src
mkdir -p lldb.src


python=`which python`

$python ./build.py clang all
$python ./build.py clang all --assertions


$python ./build.py clang all --lto


$python ./build.py clang build
$python ./build.py clang test

echo "############ CMAKE ##############"

$python ./build.py cmake all
$python ./build.py cmake build
$python ./build.py cmake test
$python ./build.py cmake testlong


echo "############ SRC TREE ##############"

$python ./build.py derive
$python ./build.py derive-lldb
$python ./build.py derive-llvm+clang

#Clean up.

rm -rf host-compiler
rm -rf llvm.src
rm -rf clang.src
rm -rf libcxx.src
rm -rf compiler-rt.src
rm -rf debuginfo-tests.src
rm -rf clang-tools-extra.src
rm -rf lldb.src