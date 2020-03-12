#!/usr/bin/python

import os
import sys
import annotated_builder


def main(argv):
    ap = annotated_builder.get_argument_parser()
    ap.add_argument('--asan', action='store_true', default=False)
    args = ap.parse_args(argv[1:])

    extra_cmake_args = ['-DCMAKE_BUILD_TYPE=Debug']
    if args.asan:
        extra_cmake_args.append('-DLLVM_USE_SANITIZER=Address')

    projects = ['llvm', 'libc']
    check_targets = ['check-libc']

    builder = annotated_builder.AnnotatedBuilder()
    builder.run_steps(projects=projects,
                      check_targets=check_targets,
                      extra_cmake_args=extra_cmake_args)


if __name__ == '__main__':
    sys.path.append(os.path.dirname(__file__))
    sys.exit(main(sys.argv))
