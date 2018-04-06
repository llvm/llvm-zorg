from __future__ import print_function

import util

import argparse
import errno
import os
import re
import shutil
import subprocess
import sys

from os.path import join as pjoin

def get_argument_parser(*args, **kwargs):
    ap = argparse.ArgumentParser(*args, **kwargs)
    ap.add_argument('--jobs', help='Number of concurrent jobs to run')
    return ap


class AnnotatedBuilder:

    """
    Builder implementation that can be used with Buildbot's AnnotatedCommand.
    Usage:
      builder = AnnotatedBuilder()
      builder.run_steps()

    See run_steps() for parameters that can be passed to alter the behavior.
    """

    def halt_on_failure(self):
        util.report('@@@HALT_ON_FAILURE@@@')

    def report_build_step(self, step):
        util.report('@@@BUILD_STEP %s@@@' % (step,))

    def report_step_exception(self, exn=None):
        if exn:
            util.report(str(exn))
        util.report('@@@STEP_EXCEPTION@@@')

    def build_and_check_stage(
        self,
        stage,
        build_dir,
        source_dir,
        cmake_args,
        check_targets=None,
        clean=True,
        jobs=None):
        stage_name = 'stage %s' % (stage,)
        if clean:
            self.clean_build_dir(stage_name, build_dir)
        self.cmake(stage_name, build_dir, source_dir, cmake_args=cmake_args)
        self.build(stage_name, build_dir, jobs)
        if check_targets is not None:
            self.check(stage_name, build_dir, check_targets, jobs)

    def build_and_check_stages(
        self,
        stages,
        build_dir,
        source_dir,
        cmake_args,
        extra_cmake_args,
        c_compiler,
        cxx_compiler,
        linker,
        check_stages,
        check_targets,
        stage1_extra_cmake_args,
        jobs=None):
        if jobs:
            cmake_args = [ '-DLLVM_LIT_ARGS=-sv -j %s' % (jobs,) ] + cmake_args
        for stage in range(1, stages + 1):
            stage_build_dir = pjoin(build_dir, 'stage%s' % (stage,))
            if stage == 1:
                s_cmake_args = cmake_args + stage1_extra_cmake_args
                stage_clean = str(
                    os.environ.get('BUILDBOT_CLOBBER', '')) != ''
            else:
                previous_stage_bin = pjoin(
                    build_dir, 'stage%s' % (stage - 1,), 'bin')
                s_cmake_args = self.stage_cmake_args(
                    cmake_args,
                    extra_cmake_args,
                    c_compiler,
                    cxx_compiler,
                    linker,
                    previous_stage_bin)
                stage_clean = True
            if check_stages[stage - 1]:
                stage_check_targets = check_targets
            else:
                stage_check_targets = None
            self.build_and_check_stage(
                stage,
                stage_build_dir,
                source_dir,
                s_cmake_args,
                stage_check_targets,
                stage_clean,
                jobs)

    def build(self, stage_name, build_dir, jobs=None):
        self.report_build_step('%s build' % (stage_name,))
        self.halt_on_failure()
        cmd = ['ninja']
        if jobs:
            cmd += ['-j', str(jobs)]
        util.report_run_cmd(cmd, cwd=build_dir)

    def check(self, stage_name, build_dir, check_targets, jobs=None):
        self.report_build_step('%s check' % (stage_name,))
        self.halt_on_failure()
        cmd = ['ninja']
        if jobs:
            cmd += ['-j', str(jobs)]
        cmd += check_targets
        util.report_run_cmd(cmd, cwd=build_dir)

    def clean_build_dir(self, stage_name, build_dir):
        self.report_build_step('%s clean' % (stage_name,))
        self.halt_on_failure()
        try:
            util.clean_dir(build_dir)
        except Exception as e:
          self.report_step_exception(e)
          raise

    def cmake(
        self,
        stage_name,
        build_dir,
        source_dir,
        cmake='cmake',
        cmake_args=None):
        self.report_build_step('%s cmake' % (stage_name,))
        self.halt_on_failure()
        cmd = [cmake]
        if cmake_args is not None:
            cmd += cmake_args
        cmd += [source_dir]
        util.mkdirp(build_dir)
        util.report_run_cmd(cmd, cwd=build_dir)

    def cmake_compiler_flags(
        self,
        c_compiler,
        cxx_compiler,
        linker=None,
        path=None):
        c_compiler_flag = '-DCMAKE_C_COMPILER=%s' % (
            util.cmake_pjoin(path, c_compiler),)
        cxx_compiler_flag = '-DCMAKE_CXX_COMPILER=%s' % (
            util.cmake_pjoin(path, cxx_compiler),)
        if linker is None:
            linker_flag = ''
        else:
            linker_flag = '-DCMAKE_LINKER=%s' % (
                util.cmake_pjoin(path, linker),)
        if os.name == 'nt':
            c_compiler_flag += '.exe'
            cxx_compiler_flag += '.exe'
            linker_flag += '.exe'
        flags = [
            c_compiler_flag,
            cxx_compiler_flag,
        ]
        if linker is not None:
            flags += [
                linker_flag,
            ]
        return flags

    def compiler_binaries(self, compiler):
        """
        Given a symbolic compiler name, return a tuple
        (c_compiler, cxx_compiler) with the names of the binaries
        to invoke.
        """
        if compiler == 'clang':
            return ('clang', 'clang++')
        elif compiler == 'clang-cl':
            return ('clang-cl', 'clang-cl')
        else:
            raise ValueError('Unsupported compiler type: %s' % (compiler,))

    def stage_cmake_args(
        self,
        cmake_args,
        extra_cmake_args,
        c_compiler,
        cxx_compiler,
        linker,
        previous_stage_bin):
        return (
            cmake_args + [
                '-DCMAKE_AR=%s' % (
                    util.cmake_pjoin(previous_stage_bin, 'llvm-ar'),),
                '-DCMAKE_RANLIB=%s' % (
                    util.cmake_pjoin(previous_stage_bin, 'llvm-ranlib'),),
            ] + self.cmake_compiler_flags(
                c_compiler, cxx_compiler, linker, previous_stage_bin) +
            extra_cmake_args)

    def set_environment(self, env=None, vs_tools=None, arch=None):
        self.report_build_step('set-environment')
        try:
            new_env = {
                'TERM': 'dumb',
            }
            if os.name == 'nt':
                if vs_tools is None:
                    vs_tools = os.path.expandvars('%VS140COMNTOOLS%')
                if arch is None:
                    arch = os.environ['PROCESSOR_ARCHITECTURE'].lower()
                else:
                    arch = arch.lower()
                vcvars_path = pjoin(
                    vs_tools, '..', '..', 'VC', 'vcvarsall.bat')
                cmd = util.shquote_cmd([vcvars_path, arch]) + ' && set'
                output = subprocess.check_output(cmd, shell=True)
                for line in output.splitlines():
                    var, val = line.split('=', 1)
                    new_env[var] = val

            if env is not None:
                new_env.epdate(env)

            for (var, val) in new_env.items():
                os.environ[var] = val

            for var in sorted(os.environ.keys()):
                util.report('%s=%s' % (var, os.environ[var]))
        except Exception as e:
            self.report_step_exception(e)
            raise

    def update_sources(self, source_dir, projects, revision=None, svn='svn'):
        self.report_build_step('update-sources')
        self.halt_on_failure()
        try:
            for (project, path, uri) in projects:
                if path is None:
                    path = source_dir
                elif not os.path.isabs(path):
                    path = pjoin(source_dir, path)
                util.report(
                    "Updating %s at %s from %s" % (project, util.shquote(path), uri))
                if revision is None:
                    revision_args = []
                else:
                    revision_args = ['-r', revision]
                if os.path.exists(pjoin(path, '.svn')):
                    cmd = [svn, 'up'] + revision_args
                else:
                    util.mkdirp(path)
                    cmd = [svn, 'co'] + revision_args + [uri, '.']
                util.report_run_cmd(cmd, cwd=path)
        except Exception as e:
            self.report_step_exception(e)
            raise

    def run_steps(
        self,
        stages=1,
        check_targets=None,
        check_stages=None,
        extra_cmake_args=None,
        stage1_extra_cmake_args=None,
        revision=None,
        compiler='clang',
        linker='ld.lld',
        env=None,
        jobs=None):
        """
        stages: number of stages to run (default: 1)
        check_targets: targets to run during the check phase (default: ['check-all'])
        check_stages: stages for which to run the check phase
            (array of bool, default: all True)
        extra_cmake_args: extra arguments to pass to cmake (default: [])
        stage1_extra_cmake_args: extra arguments to pass to cmake for stage 1
            (default: use extra_cmake_args)
        revision: revision to check out (default: os.environ['BUILDBOT_REVISION'],
            or, if that is unset, the latest revision)
        compiler: compiler to use after stage 1
            ('clang' or 'clang-cl'; default 'clang')
        linker: linker to use after stage 1
            (None (let cmake choose) or 'lld' (default))
        env: environment overrides (map; default is no overrides)
        jobs: number of jobs to run concurrently (default: determine automatically)
        """

        # Set defaults.
        if check_targets is None:
            check_targets = ['check-all']
        if check_stages is None:
            check_stages = [True] * stages
        if extra_cmake_args is None:
            extra_cmake_args = []
        if revision is None:
            revision = os.environ.get('BUILDBOT_REVISION')
        if stage1_extra_cmake_args is None:
            stage1_extra_cmake_args = extra_cmake_args

        c_compiler, cxx_compiler = self.compiler_binaries(compiler)

        self.set_environment(env)

        # Update sources.
        cwd = os.getcwd()
        source_dir = pjoin(cwd, 'llvm.src')
        build_dir = pjoin(cwd, 'build')
        svn_uri_pattern = 'http://llvm.org/svn/llvm-project/%s/trunk'
        projects = []
        projects.append(('llvm', None, svn_uri_pattern % ('llvm',)))
        projects.append(
            ('clang', pjoin('tools', 'clang'), svn_uri_pattern % ('cfe',)))
        cmake_args = ['-GNinja']
        for p in ['lld']:
            projects.append((p, pjoin('tools', p), svn_uri_pattern % (p,)))

        self.update_sources(source_dir, projects, revision=revision)

        # Build and check stages.
        self.build_and_check_stages(
            stages,
            build_dir,
            source_dir,
            cmake_args,
            extra_cmake_args,
            c_compiler,
            cxx_compiler,
            linker,
            check_stages,
            check_targets,
            stage1_extra_cmake_args,
            jobs)

        return 0


def main(argv):
    ap = get_argument_parser()
    args = ap.parse_args(argv[1:])
    builder = AnnotatedBuilder()
    builder.run_steps(jobs=args.jobs)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
