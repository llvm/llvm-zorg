#!/usr/bin/python

import os
import sys
import annotated_builder


def main(argv):
    ap = annotated_builder.get_argument_parser()
    args = ap.parse_args(argv[1:])

    stages = 2
    stage1_extra_cmake_args = [
        '-DCMAKE_BUILD_TYPE=Release',
        '-DLLVM_TARGETS_TO_BUILD=X86',
    ]
    extra_cmake_args = stage1_extra_cmake_args + [
        '-DLLVM_ENABLE_LTO=thin',
        '-DLLVM_USE_LINKER=lld',
    ]
    check_targets = ['check-llvm', 'check-clang', 'check-lld']
    check_stages = [True] * stages
    check_stages[0] = False
    if os.name == 'nt':
        compiler = 'clang-cl'
        linker = 'lld-link'
    else:
        compiler = 'clang'
        linker = 'ld.lld'

    builder = annotated_builder.AnnotatedBuilder()
    builder.run_steps(stages=stages,
                      extra_cmake_args=extra_cmake_args,
                      stage1_extra_cmake_args=stage1_extra_cmake_args,
                      check_targets=check_targets,
                      check_stages=check_stages,
                      compiler=compiler,
                      linker=linker,
                      jobs=args.jobs)


if __name__ == '__main__':
    sys.path.append(os.path.dirname(__file__))
    sys.exit(main(sys.argv))
