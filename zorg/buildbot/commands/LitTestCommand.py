import re
import urllib
from os.path import basename
import buildbot
import buildbot.status.builder
from buildbot.status.results import FAILURE, SUCCESS
import buildbot.steps.shell
from buildbot.process.buildstep import LogLineObserver
from buildbot.steps.shell import Test

class LitLogObserver(LogLineObserver):
  # Regular expressions for a regular test line.
  kTestLineRE = re.compile(r'(\w+): (.*) \(.*\)')

  # Regular expressions for verbose log start and stop markers. Verbose log
  # output always immediately follow a test.
  kTestVerboseLogStartRE = re.compile(r"""\*{4,80} TEST '(.*)' .*""")
  kTestVerboseLogStopRE = re.compile(r"""\*{10,80}""")

  # These are the codes for which we will include the log output in the buildbot
  # step results.
  failingCodes = set(['FAIL', 'XPASS', 'KPASS', 'UNRESOLVED', 'TIMEOUT'])
  # Regular expressions for start of summary marker.
  kStartSummaryRE = re.compile(r'^Failing Tests \(\d*\)$')

  def __init__(self, maxLogs=None, parseSummaryOnly=False):
    LogLineObserver.__init__(self)
    self.resultCounts = {}
    self.maxLogs = maxLogs
    self.numLogs = 0

    # If non-null, a tuple of the last test code and name.
    self.lastTestResult = None

    # If non-null, a list of lines in the current log.
    self.activeVerboseLog = None
    # Current line will be parsed as result steps only if parserStarted is True
    self.parserStarted = not parseSummaryOnly

  def hadFailure(self):
    for code in self.failingCodes:
      if self.resultCounts.get(code):
        return True

  def handleVerboseLogLine(self, line):
    # Append to the log.
    self.activeVerboseLog.append(line)

    # If this is a stop marker, process the test info.
    if self.kTestVerboseLogStopRE.match(line):
      self.testInfoFinished()

  def testInfoFinished(self):
    # We have finished getting information for one test, handle it.
    code, name = self.lastTestResult

    # If the test failed, add a log entry for it (unless we have reached the
    # max).
    if code in self.failingCodes and (self.maxLogs is None or
                                      self.numLogs < self.maxLogs):
      # If a verbose log was not provided, just add a one line description.
      if self.activeVerboseLog is None:
        self.activeVerboseLog = ['%s: %s' % (code, name)]

      # Add the log to the build status.
      # Make the test name short, the qualified test name is in the log anyway.
      # Otherwise, we run out of the allowed name length on some hosts.
      name_part = name.rpartition('::')
      self.step.addCompleteLog(
                  name_part[0].strip() + name_part[1] + basename(name_part[2]),
                  '\n'.join(self.activeVerboseLog))
      self.numLogs += 1

    # Reset the current state.
    self.lastTestResult = None
    self.activeVerboseLog = None

  def outLineReceived(self, line):
    # If we are inside a verbose log, just accumulate lines until we reach the
    # stop marker.
    if self.activeVerboseLog is not None:
      self.handleVerboseLogLine(line)
      return

    # Check for the test verbose log start marker.
    m = self.kTestVerboseLogStartRE.match(line.strip())
    if m:
      self.activeVerboseLog = [line]
      if m.group(1) != self.lastTestResult[1]:
        # This is bogus, the verbose log test name doesn't match what we
        # expect. Just note it in the log but otherwise accumulate as normal.
        self.activeVerboseLog.append(
          "error: verbose log output name didn't match expected test name")
      return

    # Otherwise, if we had any previous test consider it finished.
    #
    # FIXME: This assumes that we will always have at least one line following
    # the last test result to properly record each test; we could fix this if
    # buildbot provided us a hook for when the log is done.
    if self.lastTestResult:
      self.testInfoFinished()

    if self.kStartSummaryRE.match(line):
      self.parserStarted = True;

    #Assign result line only if summary marker has been matched
    #Or if all lines should be parsed
    if self.parserStarted is True:
      # Check for a new test status line.
      m = self.kTestLineRE.match(line.strip())
      if m:
        # Remember the last test result and update the result counts.
        self.lastTestResult = (code, name) = m.groups()
        self.resultCounts[code] = self.resultCounts.get(code, 0) + 1
        return

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

  def __init__(self, ignore=[], flaky=[], max_logs=20, parseSummaryOnly=False,
               *args, **kwargs):
    Test.__init__(self, *args, **kwargs)
    self.maxLogs = int(max_logs)
    self.logObserver = LitLogObserver(self.maxLogs, parseSummaryOnly)
    self.addFactoryArguments(max_logs=max_logs)
    self.addFactoryArguments(parseSummaryOnly=parseSummaryOnly)
    self.addLogObserver('stdio', self.logObserver)

  def evaluateCommand(self, cmd):
    # Always report failure if the command itself failed.
    if cmd.rc != 0:
      return FAILURE

    # Otherwise, report failure if there were failures in the log.
    if self.logObserver.hadFailure():
      return FAILURE

    return SUCCESS

  def describe(self, done=False):
    description = Test.describe(self, done)
    for name, count in self.logObserver.resultCounts.iteritems():
        if name in self.resultNames:
            description.append('{0} {1}'.format(count, self.resultNames[name]))
        else:
            description.append('Unexpected test result output ' + name)
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
    self.assertEqual(obs.step.logs, [('test-two', 'FAIL: test-two')])

  def test_verbose_logs(self):
    obs = self.parse_log("""
FAIL: test-one (1 of 3)
FAIL: test-two (2 of 3)
**** TEST 'test-two' FAILED ****
bla bla bla
**********
FAIL: test-three (3 of 3)
""")

    self.assertEqual(obs.resultCounts, { 'FAIL' : 3 })
    self.assertEqual(obs.step.logs, [
        ('test-one', 'FAIL: test-one'),
        ('test-two', """\
**** TEST 'test-two' FAILED ****
bla bla bla
**********"""),
        ('test-three', 'FAIL: test-three')])

class TestCommand(unittest.TestCase):
  def parse_log(self, text, **kwargs):
    cmd = LitTestCommand(**kwargs)
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

  def test_max_logs(self):
    cmd = self.parse_log("""
FAIL: test-one (1 of 2)
FAIL: test-two (2 of 2)
""", max_logs=1)
    self.assertEqual(cmd.logObserver.step.logs, [('test-one', 'FAIL: test-one')])

if __name__ == '__main__':
  unittest.main()
