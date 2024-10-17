#!/bin/bash

# Invoke as: ./run_lldb_metrics.sh /path/to/llvm/under/test /path/to/debug/llvm/build

set -xeou pipefail

# This directory contains the LLDB under test for which we collect metrics.
LLVM_BUILD_DIR=$1
if [ -z "${LLVM_BUILD_DIR}" ] || [ ! -d "${LLVM_BUILD_DIR}" ]; then
    echo "Invalid path to host Clang specified: ${LLVM_BUILD_DIR}"
    exit 1
fi

# This directory contains a debug build of clang and LLDB. We attach
# the LLDB under test (in LLVM_BUILD_DIR) to these debug binaries
# to collect metrics.
DEBUG_BUILD_DIR=$2
if [ -z "${DEBUG_BUILD_DIR}" ] || [ ! -d "${DEBUG_BUILD_DIR}" ]; then
    echo "Invalid path to host debug Clang/LLDB specified: ${DEBUG_BUILD_DIR}"
    exit 1
fi

ARTIFACTS=/tmp/lldb-metrics
RESULTS_DIR=${ARTIFACTS}/results
HYPERFINE_RUNS=5
HYPERFINE_WARMUP=3
SYSROOT=`xcrun --show-sdk-path`
TEST_COMPILE_FLAGS="-g -O0 -isysroot ${SYSROOT}"
TEST_SRC_FILE=${ARTIFACTS}/main.cpp

profile_clang() {
    local test_case_name="clang_$1"

    # Invocation to be profiled.
    local profile_invocation="$2"

    # Debuggee that LLDB will launch.
    local debuggee_invocation="${DEBUG_BUILD_DIR}/bin/clang++ -c ${TEST_COMPILE_FLAGS} ${TEST_SRC_FILE} -o $ARTIFACTS/a.o"

    # Where to write the 'statistics dump' output to.
    local stats_filename="${RESULTS_DIR}/${test_case_name}.json"

    # Run test-case and collect statistics.
    eval "${profile_invocation} -o 'script -- f=open(\"${stats_filename}\",\"w\"); lldb.debugger.SetOutputFileHandle(f,True); lldb.debugger.HandleCommand(\"statistics dump\")' --batch -- ${debuggee_invocation}"

    [[ -f $stats_filename ]] && cat $stats_filename
}

profile_lldb() {
    local test_case_name="lldb_$1"

    # Invocation to be profiled.
    local profile_invocation="$2"

    local debuggee="${ARTIFACTS}/a.out"
    ${DEBUG_BUILD_DIR}/bin/clang++ -isysroot ${SYSROOT} ${TEST_COMPILE_FLAGS} ${TEST_SRC_FILE} -o ${debuggee}

    # Debuggee that LLDB will launch.
    local debuggee_invocation="${DEBUG_BUILD_DIR}/bin/lldb ${debuggee} -o 'br se -p return' -o run -o 'expr fib(1)'"

    # Where to write the 'statistics dump' output to.
    local stats_filename="${RESULTS_DIR}/${test_case_name}.json"

    # Run test-case and collect statistics.
    eval "${profile_invocation} -o 'script -- f=open(\"${stats_filename}\",\"w\"); lldb.debugger.SetOutputFileHandle(f,True); lldb.debugger.HandleCommand(\"statistics dump\")' --batch -- ${debuggee_invocation}"

    [[ -f $stats_filename ]] && cat $stats_filename
}

# Clean previous results

rm -rf $ARTIFACTS
mkdir $ARTIFACTS
mkdir $RESULTS_DIR

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

# Benchmarks
# ==========
#
# Attaches the LLDB under test to a debug build of Clang/LLDB. We stop in a member
# function of a "large" class (in this case clang::CodeGen::CodeGenFunction or
# lldb_private::ClangASTSource). We then run various LLDB commands and collect a
# `statistics dump` afterwards. Currently the scenarios are:
# 
# * frame_status: this just runs up to (and including) stopping in
#                 a function, which then triggers formatting of the frame
#                 status (which can be non-trivial since we trigger
#                 data-formatters for function arguments and completion of
#                 argument variables).
#
# * expr_deref: dereferences the "llvm::Function *Fn" function argument
#               through the expression evaluator. This will trigger completion
#               of the CodeGenFunction context and the llvm::Function class.
#
# * expr_method_call: call a method on Fn->isVarArg(). Similar to "expr_deref"
#                     just with an additional function call.
#
# * expr_re_eval: dereference "llvm::Function *Fn" multiple times consecutively,
#                 in the hopes that some of the work doesn't have to be re-done.
#
# * expr_two_stops: We run the "expr_deref", and then continue to another breakpoint
#                   inside LLVM and run another set of expressions, testing the expression
#                   evaluator's behaviour when stopping in different LLDB modules.
#
# * var_then_expr: Run "frame var" followed by expression evaluation.
#
# * var: Run "frame var", which triggers data-formatters and completion of local
#        variables.

# Clang benchmarks
# ================

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
# ===============

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
