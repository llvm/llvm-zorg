#!/usr/bin/python

import os
import sys
import annotated_builder

def main(argv):
    ap = annotated_builder.get_argument_parser()
    args = ap.parse_args(argv[1:])

    # TODO: Add back debuginfo-tests once it works.
    projects = ['llvm', 'clang', 'clang-tools-extra', 'lld']
    stages = 2
    extra_cmake_args = [
        '-DCMAKE_BUILD_TYPE=Release',
        '-DLLVM_ENABLE_PDB=ON',
        '-DLLVM_ENABLE_ASSERTIONS=ON',
        '-DLLVM_TARGETS_TO_BUILD=all',
    ]
    check_targets = [
            'check-llvm',
            'check-clang',
            'check-clang-tools',
            'check-clangd',
            'check-lld',
            #'check-debuginfo', # TODO: Add back soon.
            ]

    # Check both stage 1 and stage 2.
    check_stages = [True] * stages

    compiler = 'clang-cl'
    linker = 'lld-link'

    builder = annotated_builder.AnnotatedBuilder()
    builder.run_steps(projects=projects,
                      stages=stages,
                      extra_cmake_args=extra_cmake_args,
                      check_targets=check_targets,
                      check_stages=check_stages,
                      compiler=compiler,
                      linker=linker,
                      jobs=args.jobs)


if __name__ == '__main__':
    sys.path.append(os.path.dirname(__file__))
    sys.exit(main(sys.argv))
