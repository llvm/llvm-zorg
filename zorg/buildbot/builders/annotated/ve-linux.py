#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import traceback
import util
from contextlib import contextmanager


def main(argv):
    # Avoid a buildmaster update by hard-coding this for now.
    makefile = 've-linux-steps.make'

    # TODO: Make Makefile configurable and update buildmaster.
    # ap = argparse.ArgumentParser()
    # ap.add_argument('makefile', help='The Makefile to use. (relative to annoted/ folder of llvm-zorg).')
    # args, _ = ap.parse_known_args()
    # makefile = args.makefile

    worker_dir = os.path.abspath(os.path.join('..'))
    annotated_dir = os.path.join(worker_dir, 'llvm-zorg', 'zorg', 'buildbot', 'builders', 'annotated')
    makefile_path = os.path.join(annotated_dir, makefile)

    # Query step list from makefile.
    build_targets=[]
    with step('prepare', halt_on_fail=True):
        build_targets = get_steps(makefile_path)

    make_vars = {
      'BUILDROOT' : os.path.join(worker_dir, 'build')
    }

    for target in build_targets:
        with step(target, halt_on_fail=True):
            make_cmd = build_make_cmd(makefile_path, target, make_vars)
            run_command(make_cmd, cwd='.')

@contextmanager
def step(step_name, halt_on_fail=False):
    util.report('@@@BUILD_STEP {}@@@'.format(step_name))
    if halt_on_fail:
        util.report('@@@HALT_ON_FAILURE@@@')
    try:
        yield
    except Exception as e:
        if isinstance(e, subprocess.CalledProcessError):
            util.report(
                '{} exited with return code {}.'.format(e.cmd, e.returncode)
            )
        util.report('The build step threw an exception...')
        traceback.print_exc()

        util.report('@@@STEP_FAILURE@@@')
    finally:
        sys.stdout.flush()


def get_steps(makefile):
    try:
        make_cmd = build_make_cmd(makefile, 'get-steps')
        raw_steps = capture_cmd_stdout(make_cmd)
        return raw_steps.decode('utf-8').split('\n')
    except:
        return []

def build_make_cmd(makefile, target, make_vars={}):
    make_cmd = ['make', '-f', makefile]
    if not target is None:
        make_cmd.append(target)
    for k,v in make_vars.items():
        make_cmd += ["{}={}".format(k, v)]
    return make_cmd

def capture_cmd_stdout(cmd, **kwargs):
    return subprocess.run(cmd, shell=False, check=True, stdout=subprocess.PIPE, **kwargs).stdout

def run_command(cmd, directory='.', **kwargs):
    util.report_run_cmd(cmd, cwd=directory, **kwargs)

if __name__ == '__main__':
    sys.path.append(os.path.dirname(__file__))
    sys.exit(main(sys.argv))
