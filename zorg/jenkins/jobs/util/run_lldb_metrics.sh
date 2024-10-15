#!/bin/bash

set -xeou pipefail

LLVM_BUILD_DIR=$1
if [ -z "${LLVM_BUILD_DIR}" ]; then
    echo "Path to host Clang not specified."
    exit 1
fi

DEBUG_BUILD_DIR=$2
if [ -z "${DEBUG_BUILD_DIR}" ]; then
    echo "Path to debug Clang/LLDB not specified."
    exit 1
fi

ARTIFACTS=/tmp/lldb-metrics
CSV_DIR=${ARTIFACTS}/csv
HYPERFINE_RUNS=5
HYPERFINE_WARMUP=3
SYSROOT=`xcrun --show-sdk-path`
TEST_COMPILE_FLAGS="-g -O0 -isysroot ${SYSROOT}"
TEST_SRC_FILE=${ARTIFACTS}/main.cpp

profile() {
  local test_case_name=$1
  if [ -z "${test_case_name}" ]; then
      echo "ERROR: Test-case name is empty."
      return
  fi

  local csv_path="${CSV_DIR}/${test_case_name}.csv"
  if [ -f ${csv_path} ]; then
      echo "Results already exist at '${csv_path}'."
      return
  fi

  hyperfine \
      --warmup ${HYPERFINE_WARMUP} \
      --runs ${HYPERFINE_RUNS} \
      --export-csv ${csv_path} \
      --shell=bash \
      -- \
      "$2"

  [[ -f $csv_path ]] && cat $csv_path
}

profile_clang() {
    local test_case_name="clang_$1"

    # Invocation to be profiled.
    local profile_invocation=$2

    # Debuggee that LLDB will launch.
    local debuggee_invocation="${DEBUG_BUILD_DIR}/bin/clang++ -c ${TEST_COMPILE_FLAGS} ${TEST_SRC_FILE} -o $ARTIFACTS/a.o"

    # Where to write the 'statistics dump' output to.
    local stats_filename="${CSV_DIR}/${test_case_name}.json"

    # Launch hyperfine.
    profile \
        $test_case_name \
        "${profile_invocation} -o 'script -- f=open(\"${stats_filename}\",\"w\"); lldb.debugger.SetOutputFileHandle(f,True); lldb.debugger.HandleCommand(\"statistics dump\")' --batch -- ${debuggee_invocation}"

    [[ -f $stats_filename ]] && cat $stats_filename
}

profile_lldb() {
    local test_case_name="lldb_$1"

    # Invocation to be profiled.
    local profile_invocation=$2

    local debuggee="${ARTIFACTS}/a.out"
    if [ ! -f "${debuggee}" ]; then
        ${DEBUG_BUILD_DIR}/bin/clang++ -isysroot ${SYSROOT} ${TEST_COMPILE_FLAGS} ${TEST_SRC_FILE} -o ${debuggee}
    fi

    # Debuggee that LLDB will launch.
    local debuggee_invocation="${DEBUG_BUILD_DIR}/bin/lldb ${debuggee} -o 'br se -p return' -o run -o 'expr fib(1)'"

    # Where to write the 'statistics dump' output to.
    local stats_filename="${CSV_DIR}/${test_case_name}.json"

    # Launch hyperfine.
    profile \
        $test_case_name \
        "${profile_invocation} -o 'script -- f=open(\"${stats_filename}\",\"w\"); lldb.debugger.SetOutputFileHandle(f,True); lldb.debugger.HandleCommand(\"statistics dump\")' --batch -- ${debuggee_invocation}"

    [[ -f $stats_filename ]] && cat $stats_filename
}

# Clean previous results

rm -rf $ARTIFACTS
mkdir $ARTIFACTS
mkdir $CSV_DIR

cat >${TEST_SRC_FILE} <<EOL
#include <map>

int fib(int n) {
    static auto cache = [] {
        auto ans = std::map<int, int>();
        ans[0] = 0;
        ans[1] = 1;
        return ans;
    }();
    if (auto it = cache.find(n); it != cache.end()) return it->second;
    auto ans = fib(n - 1) + fib(n - 2);
    cache[ans] = ans;
    return ans;
}

int main() {
    fib(5);
    return 0;
}
EOL

# Clang benchmarks

profile_clang \
    "frame_status" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b CodeGenFunction::GenerateCode' -o run"

profile_clang \
    "expr_deref" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b CodeGenFunction::GenerateCode' -o run -o 'expr *Fn'"

profile_clang \
    "expr_method_call" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b CodeGenFunction::GenerateCode' -o run -o 'expr Fn->isVarArg()'"

profile_clang \
    "expr_re_eval" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b CodeGenFunction::GenerateCode' -o run -o 'expr *Fn' -o 'expr *Fn'"

profile_clang \
    "expr_two_stops" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b CodeGenFunction::GenerateCode' -o run -o 'expr *Fn' -o 'br del 1' -o 'b AsmPrinter::emitFunctionBody' -o c -o 'expr this->isVerbose()' -o 'expr TM'"

profile_clang \
    "var_then_expr" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b CodeGenFunction::GenerateCode' -o run -o up -o 'frame var' -o down -o 'expr *this'"

profile_clang \
    "var" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b CodeGenFunction::GenerateCode' -o run -o 'frame var'"

# LLDB benchmarks

profile_lldb \
    "frame_status" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b ClangASTSource::FindExternalVisibleDeclsByName' -o run"

profile_lldb \
    "expr_deref" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b ClangASTSource::FindExternalVisibleDeclsByName' -o run -o 'expr m_active_lexical_decls'"

profile_lldb \
    "expr_method_call" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b ClangASTSource::FindExternalVisibleDeclsByName' -o run -o 'expr clang_decl_name.getAsString()'"

profile_lldb \
    "expr_re_eval" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b ClangASTSource::FindExternalVisibleDeclsByName' -o run -o 'expr m_active_lexical_decls' -o 'expr m_active_lexical_decls'"

profile_lldb \
    "expr_two_stops" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b ClangASTSource::FindExternalVisibleDeclsByName' -o run -o 'expr m_active_lexical_decls' -o 'b CodeGeneratorImpl::HandleTranslationUnit' -o 'br del 1' -o c -o 'expr Builder' -o 'expr Ctx.getLangOpts()'"

profile_lldb \
    "var_then_expr" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b ClangASTSource::FindExternalVisibleDeclsByName' -o run -o up -o 'frame var' -o down -o 'expr *this'"

profile_lldb \
    "var" \
    "${LLVM_BUILD_DIR}/bin/lldb -o 'b ClangASTSource::FindExternalVisibleDeclsByName' -o run -o 'frame var'"
