#!/usr/bin/python

import os
import subprocess
import sys

THIS_DIR=os.path.dirname(sys.argv[0])


def bash(path):
    return 'bash ' + os.path.join(THIS_DIR, path)

def cmd_call(path):
    return 'call ' + os.path.join(THIS_DIR, path)

BOT_ASSIGNMENT = {
    'sanitizer-ppc64le-linux': bash('buildbot_cmake.sh'),
    'sanitizer-ppc64-linux1': bash('buildbot_cmake.sh'),
    'sanitizer-x86_64-linux': bash('buildbot_cmake.sh'),
    'sanitizer-x86_64-linux-bootstrap': bash('buildbot_bootstrap.sh'),
    'sanitizer-x86_64-linux-fast': bash('buildbot_fast.sh'),
    'sanitizer-x86_64-linux-autoconf': bash('buildbot_standard.sh'),
    'sanitizer-x86_64-linux-fuzzer': bash('buildbot_fuzzer.sh'),
}

BOT_ADDITIONAL_ENV = {
    'sanitizer-ppc64le-linux': { 'HAVE_NINJA': '0' },
    'sanitizer-ppc64-linux1': { 'HAVE_NINJA': '0' },
    'sanitizer-x86_64-linux': { 'BUILD_ANDROID' : '1', 'RUN_ANDROID' : '1', 'HAVE_NINJA' : '1' },
    'sanitizer-x86_64-linux-bootstrap': {},
    'sanitizer-x86_64-linux-fast': {},
    'sanitizer-x86_64-linux-autoconf': { 'CHECK_TSAN': '1', 'BUILD_ASAN_ANDROID' : '1' },
    'sanitizer-x86_64-linux-fuzzer': {},
}

def Main():
  builder = os.environ.get('BUILDBOT_BUILDERNAME')
  print "builder name: %s" % (builder)
  cmd = BOT_ASSIGNMENT.get(builder)
  if not cmd:
    sys.stderr.write('ERROR - unset/invalid builder name\n')
    sys.exit(1)

  print "%s runs: %s\n" % (builder, cmd)
  sys.stdout.flush()

  bot_env = os.environ
  add_env = BOT_ADDITIONAL_ENV.get(builder)
  for var in add_env:
    bot_env[var] = add_env[var]
  if 'TMPDIR' in bot_env:
    del bot_env['TMPDIR']

  retcode = subprocess.call(cmd, env=bot_env, shell=True)
  sys.exit(retcode)


if __name__ == '__main__':
  Main()
