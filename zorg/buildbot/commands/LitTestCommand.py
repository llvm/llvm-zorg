import re
import urllib
import buildbot
import buildbot.status.builder
from buildbot.status.results import FAILURE, SUCCESS
import buildbot.steps.shell
from buildbot.process.buildstep import LogLineObserver
from buildbot.steps.shell import Test

class LitLogObserver(LogLineObserver):
  kTestLineRE = re.compile(r'([^ ]*): (.*) \(.*.*\)')
  kTestFailureLogStartRE = re.compile(r"""\*{4,80} TEST '(.*)' .*""")
  kTestFailureLogStopRE = re.compile(r"""\*{10,80}""")
  failingCodes = set(['FAIL', 'XPASS', 'KPASS', 'UNRESOLVED'])
  def __init__(self):
    LogLineObserver.__init__(self)
    self.resultCounts = {}
    self.inFailure = None
    self.inFailureContext = False
    self.failed = False
  def outLineReceived(self, line):
    # See if we are inside a failure log.
    if self.inFailureContext:
      self.inFailure[1].append(line)
      if self.kTestFailureLogStopRE.match(line):
        self.inFailureContext = False
      return

    line = line.strip()
    if not line:
      return

    # Check for test failure logs.
    m = self.kTestFailureLogStartRE.match(line)
    if m and self.inFailure:
      if m.group(1)==self.inFailure[0]:
          self.inFailure[1].append(line)
          self.inFailureContext = True
          return
      else:
          msg = 'm[0]: %r\ninFailure[0]: %r' % (m.group(0), self.inFailure[0])
          raise ValueError, msg
    # Otherwise expect a test status line.
    m = self.kTestLineRE.match(line)
    if m:
      code, name = m.groups()
      if self.inFailure and name != self.inFailure[0]:
        name,log = self.inFailure
        self.step.addCompleteLog(name.replace('/', '__'), '\n'.join(log))
        self.inFailure = None
      if code in self.failingCodes:
        self.inFailure = (name, [line])
        self.failed = True
      if not code in self.resultCounts:
        self.resultCounts[code] = 0
      self.resultCounts[code] += 1

class LitTestCommand(Test):
  resultNames = {'FAIL':'unexpected failures',
                 'PASS':'expected passes',
                 'XFAIL':'expected failures',
                 'XPASS':'unexpected passes',
                 'KFAIL':'known failures',
                 'KPASS':'unknown passes',
                 'UNRESOLVED':'unresolved testcases',
                 'UNTESTED':'untested testcases',
                 'REGRESSED':'runtime performance regression',
                 'IMPROVED':'runtime performance improvement',
                 'UNSUPPORTED':'unsupported tests'}

  def __init__(self, ignore=[], flaky=[], max_logs=20,
               *args, **kwargs):
    Test.__init__(self, *args, **kwargs)
    self.logObserver = LitLogObserver()
    self.addLogObserver('stdio', self.logObserver)

  def evaluateCommand(self, cmd):
    # Always report failure if the command itself failed.
    if cmd.rc != 0:
      return FAILURE

    # Otherwise, report failure if there were failures in the log.
    if self.logObserver.failed:
      return FAILURE

    return SUCCESS

  def describe(self, done=False):
    description = Test.describe(self, done)
    for name, count in self.logObserver.resultCounts.iteritems():
        description.append('{0} {1}'.format(count, self.resultNames[name]))
    return description

##

import unittest

class StepProxy(object):
  def __init__(self):
    self.logs = []

  def addCompleteLog(self, name, text):
    self.logs.append((name, text))

class RemoteCommandProxy(object):
  def __init__(self, rc):
    self.rc = rc

class TestLogObserver(unittest.TestCase):
  def parse_log(self, text):
    observer = LitLogObserver()
    observer.step = StepProxy()
    for ln in text.split('\n'):
      observer.outLineReceived(ln)
    return observer

  def test_basic(self):
    obs = self.parse_log("""
PASS: test-one (1 of 3)
FAIL: test-two (2 of 3)
PASS: test-three (3 of 3)
""")

    self.assertEqual(obs.resultCounts, { 'FAIL' : 1, 'PASS' : 2 })
    self.assertEqual(obs.step.logs, [('test-two', 'FAIL: test-two (2 of 3)')])

class TestCommand(unittest.TestCase):
  def parse_log(self, text):
    cmd = LitTestCommand()
    cmd.logObserver.step = StepProxy()
    for ln in text.split('\n'):
      cmd.logObserver.outLineReceived(ln)
    return cmd

  def test_command_status(self):
    # If the command failed, the status should always be error.
    cmd = self.parse_log("")
    self.assertEqual(cmd.evaluateCommand(RemoteCommandProxy(1)), FAILURE)

    # If there were failing tests, the status should be an error (even if the
    # test command didn't report as such).
    for failing_code in ('FAIL', 'XPASS', 'KPASS', 'UNRESOLVED'):
      cmd = self.parse_log("""%s: test-one (1 of 1)""" % (failing_code,))
      self.assertEqual(cmd.evaluateCommand(RemoteCommandProxy(0)), FAILURE)

if __name__ == '__main__':
  unittest.main()
