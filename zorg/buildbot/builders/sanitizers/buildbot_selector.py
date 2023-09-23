#!/usr/bin/python

import os
import subprocess
import sys

THIS_DIR=os.path.dirname(sys.argv[0])
extra_args = sys.argv[1:]
BOT_DIR = '/b'

def in_script_dir(path):
    return os.path.join(THIS_DIR, path)

BOT_ASSIGNMENT = {
    'sanitizer-ppc64le-linux': 'buildbot_cmake.sh',
    'sanitizer-ppc64be-linux': 'buildbot_cmake.sh',
    'sanitizer-x86_64-linux': 'buildbot_cmake.sh',
    'sanitizer-x86_64-linux-fast': 'buildbot_fast.sh',
    'sanitizer-x86_64-linux-autoconf': 'buildbot_standard.sh',
    'sanitizer-x86_64-linux-fuzzer': 'buildbot_fuzzer.sh',
    'sanitizer-x86_64-linux-android': 'buildbot_android.sh',
    'sanitizer-x86_64-linux-bootstrap-asan': 'buildbot_bootstrap_asan.sh',
    'sanitizer-x86_64-linux-bootstrap-msan': 'buildbot_bootstrap_msan.sh',
    'sanitizer-x86_64-linux-bootstrap-ubsan': 'buildbot_bootstrap_ubsan.sh',
    'sanitizer-x86_64-linux-qemu': 'buildbot_qemu.sh',
    'sanitizer-aarch64-linux': 'buildbot_cmake.sh',
    'sanitizer-aarch64-linux-fuzzer': 'buildbot_fuzzer.sh',
    'sanitizer-aarch64-linux-bootstrap-asan': 'buildbot_bootstrap_asan.sh',
    'sanitizer-aarch64-linux-bootstrap-hwasan': 'buildbot_bootstrap_hwasan.sh',
    'sanitizer-aarch64-linux-bootstrap-msan': 'buildbot_bootstrap_msan.sh',
    'sanitizer-aarch64-linux-bootstrap-ubsan': 'buildbot_bootstrap_ubsan.sh',
}

BOT_ADDITIONAL_ENV = {
    'sanitizer-ppc64le-linux': {},
    'sanitizer-ppc64be-linux': {},
    'sanitizer-x86_64-linux': {},
    'sanitizer-x86_64-linux-fast': {},
    'sanitizer-x86_64-linux-autoconf': {},
    'sanitizer-x86_64-linux-fuzzer': {},
    'sanitizer-x86_64-linux-android': {},
    'sanitizer-x86_64-linux-bootstrap-asan': {},
    'sanitizer-x86_64-linux-bootstrap-msan': {},
    'sanitizer-x86_64-linux-bootstrap-ubsan': {},
    'sanitizer-x86_64-linux-qemu': { 'QEMU_IMAGE_DIR': BOT_DIR + '/qemu_image' },
    'sanitizer-aarch64-linux': {},
    'sanitizer-aarch64-linux-fuzzer': {},
    'sanitizer-aarch64-linux-bootstrap-asan': {},
    'sanitizer-aarch64-linux-bootstrap-hwasan': {},
    'sanitizer-aarch64-linux-bootstrap-msan': {},
    'sanitizer-aarch64-linux-bootstrap-ubsan': {},
}

def Main():
  builder = os.environ.get('BUILDBOT_BUILDERNAME')
  revision = os.environ.get('BUILDBOT_REVISION')
  print("builder name: %s" % (builder))
  cmd = [in_script_dir(BOT_ASSIGNMENT.get(builder))] + extra_args
  if not cmd:
    sys.stderr.write('ERROR - unset/invalid builder name\n')
    sys.exit(1)

  print("%s runs: %s\n" % (builder, ' '.join(cmd)))
  sys.stdout.flush()

  bot_env = os.environ
  bot_env['BOT_DIR'] = BOT_DIR
  add_env = BOT_ADDITIONAL_ENV.get(builder)
  for var in add_env:
    bot_env[var] = add_env[var]
  if 'TMPDIR' in bot_env:
    del bot_env['TMPDIR']

  if ':' in revision:
    cmd = [in_script_dir('buildbot_bisect_run.sh')] + cmd
  sys.exit(subprocess.call(cmd, env=bot_env))

if __name__ == '__main__':
  Main()
