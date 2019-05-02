#!/usr/bin/python

import os
import sys
import annotated_builder
import util


class SanitizerAnnotatedBuilder(annotated_builder.AnnotatedBuilder):

    """Customizes the 'build' step of the generic AnnotatedBuilder"""

    def build(self, stage_name, build_dir, jobs=None):
        # The basic idea here is to run 'ninja compiler-rt ; ninja clang lld'.
        # This ensures that portability issues in compiler-rt code are found
        # first. Then, we only build clang and lld, the primary dependencies of
        # the sanitizer test suites, to keep cycle time low. This means there
        # are still some remaining test dependencies (FileCheck) that may be
        # compiled during the check step, but there shouldn't be that many.
        self.report_build_step('%s build' % (stage_name,))
        self.halt_on_failure()
        base_cmd = ['ninja']
        if jobs:
            base_cmd += ['-j', str(jobs)]
        early_targets = ['compiler-rt']
        late_targets = ['clang', 'lld']
        util.report_run_cmd(base_cmd + early_targets, cwd=build_dir)
        util.report_run_cmd(base_cmd + late_targets, cwd=build_dir)


def main(argv):
    ap = annotated_builder.get_argument_parser()
    args = ap.parse_args(argv[1:])

    projects = ['llvm', 'clang', 'lld', 'compiler-rt']
    stages = 1
    stage1_extra_cmake_args = [
        '-DCMAKE_BUILD_TYPE=Release',
        '-DLLVM_ENABLE_PDB=ON',
        '-DLLVM_ENABLE_ASSERTIONS=ON',
        '-DLLVM_TARGETS_TO_BUILD=X86',
    ]
    extra_cmake_args = stage1_extra_cmake_args + [
        '-DLLVM_USE_LINKER=lld',
    ]
    check_targets = ['check-asan', 'check-asan-dynamic', 'check-sanitizer',
                     'check-ubsan', 'check-fuzzer', 'check-cfi',
                     'check-profile', 'check-builtins']

    # These arguments are a bit misleading, they really mean use cl.exe for
    # stage1 instead of GCC.
    compiler = 'clang-cl'
    linker = 'lld-link'

    builder = SanitizerAnnotatedBuilder()
    builder.run_steps(stages=stages,
                      projects=projects,
                      extra_cmake_args=extra_cmake_args,
                      stage1_extra_cmake_args=stage1_extra_cmake_args,
                      check_targets=check_targets,
                      compiler=compiler,
                      linker=linker,
                      jobs=args.jobs)


if __name__ == '__main__':
    sys.path.append(os.path.dirname(__file__))
    sys.exit(main(sys.argv))
