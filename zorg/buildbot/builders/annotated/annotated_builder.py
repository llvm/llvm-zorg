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

VSWHERE_PATH = "C:/Program Files (x86)/Microsoft Visual Studio/Installer/vswhere.exe"

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
        # Don't print a stack trace if a command ('ninja check') exited with a
        # non-zero exit code. That is non-exceptional expected behavior, so just
        # print the return code and fail the step.
        if exn and isinstance(exn, subprocess.CalledProcessError):
            cmd = ""
            try:
                cmd = repr(exn.cmd[0])
            except:
                pass
            util.report("Command " + cmd + " failed with return code " +
                        str(exn.returncode))
            util.report('@@@STEP_FAILURE@@@')
            return

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
                new_env.update(get_vcvars(vs_tools, arch))

            if env is not None:
                new_env.epdate(env)

            for (var, val) in new_env.items():
                os.environ[var] = val

            for var in sorted(os.environ.keys()):
                util.report('%s=%s' % (var, os.environ[var]))
        except Exception as e:
            self.report_step_exception(e)
            raise

    def update_sources(self, source_dir, projects, revision, svn='svn'):
        self.report_build_step('update-sources')
        self.halt_on_failure()

        # TODO: This needs to be updated to use the monorepo.
        # Where to check the project out relative to an LLVM checkout.
        checkout_locations = {
            'llvm': '',
            'clang': 'tools/clang',
            'lld': 'tools/lld',
            'compiler-rt': 'projects/compiler-rt',
            'debuginfo-tests': 'projects/debuginfo-tests',
            }
        # If the project is named differently in svn, put it here.
        svn_locations = { 'clang': 'cfe' }
        svn_uri_pattern = 'https://llvm.org/svn/llvm-project/%s/trunk'

        for project in projects:
            # TODO: Fail the build and report an error if we don't know the
            # checkout location.
            path = checkout_locations[project]
            if not path:
                path = source_dir
            elif not os.path.isabs(path):
                path = pjoin(source_dir, path)
            uri = svn_uri_pattern % (svn_locations.get(project, project),)
            util.report("Updating %s to %s at %s from %s" %
                        (project, revision, util.shquote(path), uri))
            if os.path.exists(pjoin(path, '.svn')):
                cmd = [svn, 'up', '-r', revision]
            else:
                util.mkdirp(path)
                cmd = [svn, 'co', '-r', revision, uri, '.']
            util.report_run_cmd(cmd, cwd=path)

    def run_steps(
        self,
        stages=1,
        projects=None,
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
        projects: which subprojects to check out from SVN
            llvm must be first in the list (default: ['llvm', 'clang', 'lld'])
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
        if not revision:
            revision = os.environ.get('BUILDBOT_REVISION')
        if stage1_extra_cmake_args is None:
            stage1_extra_cmake_args = extra_cmake_args
        if projects is None:
            projects = ['llvm', 'clang', 'lld']

        c_compiler, cxx_compiler = self.compiler_binaries(compiler)

        self.set_environment(env)

        # On Windows, if we're building clang-cl, make sure stage1 is built with
        # MSVC (cl.exe), and not gcc from mingw. CMake will prefer gcc if it is
        # available.
        if c_compiler == 'clang-cl':
            stage1_extra_cmake_args += ['-DCMAKE_C_COMPILER=cl',
                                        '-DCMAKE_CXX_COMPILER=cl']

        if not revision:
            cmd = ['svn', 'info', 'https://llvm.org/svn/llvm-project/']
            try:
                svninfo = subprocess.check_output(cmd)
            except subprocess.CalledProcessError as e:
                util.report("Failed to get most recent SVN rev: " + str(e))
                return 1
            m = re.search('Revision: ([0-9]+)', svninfo)
            if m:
                revision = m.group(1)
            else:
                util.report("Failed to find svn revision in svn info output:\n"
                            + svninfo)
                return 1
        if not revision.isdigit():
            util.report("SVN revision %s is not a positive integer" % (revision,))

        # Update sources.
        cwd = os.getcwd()
        source_dir = pjoin(cwd, 'llvm.src')
        build_dir = pjoin(cwd, 'build')
        cmake_args = ['-GNinja']

        try:
            self.update_sources(source_dir, projects, revision)

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
        except Exception as e:
            self.report_step_exception(e)
            return 1

        return 0


def get_vcvars(vs_tools, arch):
    """Get the VC tools environment using vswhere.exe from VS 2017

    This code is following the guidelines from strategy 1 in this blog post:
        https://blogs.msdn.microsoft.com/vcblog/2017/03/06/finding-the-visual-c-compiler-tools-in-visual-studio-2017/

    It doesn't work when VS is not installed at the default location.
    """
    if not arch:
        # First check the wow64 processor architecture, since python is probably
        # 32-bit, then fall back to PROCESSOR_ARCHITECTURE.
        arch = os.environ.get('PROCESSOR_ARCHITEW6432', '').lower()
        if not arch:
            arch = os.environ.get('PROCESSOR_ARCHITECTURE', '').lower()
    else:
        arch = arch.lower()

    # Use vswhere.exe if it exists.
    if os.path.exists(VSWHERE_PATH):
        cmd = [VSWHERE_PATH, "-latest", "-property", "installationPath"]
        vs_path = subprocess.check_output(cmd).strip()
        util.report("Running vswhere to find VS: " + repr(cmd))
        util.report("vswhere output: " + vs_path)
        if not os.path.isdir(vs_path):
            raise ValueError("VS install path does not exist: " + vs_path)
        vcvars_path = pjoin(vs_path, 'VC', 'Auxiliary', 'Build',
                            'vcvarsall.bat')
    elif vs_tools is None:
        vs_tools = os.path.expandvars('%VS140COMNTOOLS%')
        vcvars_path = pjoin(vs_tools, '..', '..', 'VC', 'vcvarsall.bat')

    # Newer vcvarsall.bat scripts aren't quiet, so direct them to NUL, aka
    # Windows /dev/null.
    cmd = util.shquote_cmd([vcvars_path, arch]) + ' > NUL && set'
    util.report("Running vcvars: " + cmd)
    output = subprocess.check_output(cmd, shell=True)
    new_env = {}
    for line in output.splitlines():
        var, val = line.split('=', 1)
        new_env[var] = val
    return new_env


def main(argv):
    ap = get_argument_parser()
    args = ap.parse_args(argv[1:])
    builder = AnnotatedBuilder()
    builder.run_steps(jobs=args.jobs)


if __name__ == '__main__':
    sys.exit(main(sys.argv))
