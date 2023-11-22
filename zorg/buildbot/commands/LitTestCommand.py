import re
from os.path import basename

from buildbot.process.results import SUCCESS
from buildbot.process.results import FAILURE

from buildbot.steps.shell import Test

from buildbot.process.logobserver import LogLineObserver

class LitLogObserver(LogLineObserver):
  # Regular expressions for a regular test line.
  kTestLineRE = re.compile(r'(\w+): (.*) \(.*\)')

  # Regular expressions for verbose log start and stop markers. Verbose log
  # output always immediately follow a test.
  kTestVerboseLogStartRE = re.compile(r"""\*{4,80} TEST '(.*)' .*""")
  kTestVerboseLogStopRE = re.compile(r"""\*{10,80}""")
  kTestVerboseGTestUnitRE = re.compile(r'^(.*)\/(\d+)\/(\d+)$')
  kTestVerboseGTestPathRE = re.compile(r'^(.+)\s+--gtest_filter=(\w+).(\w+)(\s|$)')

  # These are the codes for which we will include the log output in the buildbot
  # step results.
  failingCodes = set(['FAIL', 'XPASS', 'KPASS', 'UNRESOLVED', 'TIMEOUT', 'ERROR', 'NOEXE'])
  # Regular expressions for start of summary marker.
  kStartSummaryRE = re.compile(r'^Failing Tests \(\d*\)$')

  def __init__(self, maxLogs=None, parseSummaryOnly=False):
    super().__init__()
    self.resultCounts = {}
    self.maxLogs = maxLogs
    self.numLogs = 0

    # If non-null, a tuple of the last test code and name.
    self.lastTestResult = None

    # If non-null, a list of lines in the current log.
    self.activeVerboseLog = None
    self.activeVerboseGTest = None

    # Current line will be parsed as result steps only if parserStarted is True
    self.parserStarted = not parseSummaryOnly
    self.simplifiedLog = False

  def hadFailure(self):
    for code in self.failingCodes:
      if self.resultCounts.get(code):
        return True

  def handleVerboseLogLine(self, line):
    # Append to the log.
    self.activeVerboseLog.append(line)

    m = self.kTestVerboseGTestPathRE.match(line.strip())
    if m:
        self.activeVerboseGTest = [m.group(2), m.group(3)]

    # If this is a stop marker, process the test info.
    if self.kTestVerboseLogStopRE.match(line.strip()):
      self.testInfoFinished()

  def testInfoFinished(self):
    # We have finished getting information for one test, handle it.
    if self.lastTestResult:
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
          name_part2 = basename(name_part[2])

          if self.activeVerboseGTest:
              m = self.kTestVerboseGTestUnitRE.match(name_part[2].strip())
              if m:
                  name_part2 = '/'.join([basename(m.group(1)),] + self.activeVerboseGTest)

          self.step.addCompleteLog(
                      code + ': ' + name_part[0].strip() + name_part[1] + name_part2,
                      '\n'.join(self.activeVerboseLog))
          self.numLogs += 1
    else:
        if self.activeVerboseLog:
            self.activeVerboseLog.append(
              "error: missing test status line, skipping log")

    # Reset the current state.
    self.lastTestResult = None
    self.activeVerboseLog = None
    self.activeVerboseGTest = None

  def handleSimplifiedLogLine(self, line):
    # Check for test status line
    m = self.kTestLineRE.match(line.strip())
    if m:
      # Remember the last test result and update the result counts.
      self.lastTestResult = (code, name) = m.groups()
      self.resultCounts[code] = self.resultCounts.get(code, 0) + 1
      self.testInfoFinished()
    return

  def outLineReceived(self, line):
    # Assert - Lines after "Failing Test (\d)" will be summary line and will not contain verbose message
    if self.simplifiedLog is True:
      self.handleSimplifiedLogLine(line)
      return
    # If we are inside a verbose log, just accumulate lines until we reach the
    # stop marker.
    if self.activeVerboseLog is not None:
      self.handleVerboseLogLine(line)
      return

    # Check for the test verbose log start marker.
    m = self.kTestVerboseLogStartRE.match(line.strip())
    if m:
      self.activeVerboseLog = [line]
      if self.lastTestResult is None:
        if self.activeVerboseLog:
            self.activeVerboseLog.append(
              "error: missing test line before verbose log start.")
      elif m.group(1) != self.lastTestResult[1]:
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
      self.simplifiedLog = True;

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
                 'XPASS':'unexpected passes',
                 'PASS':'expected passes',
                 'XFAIL':'expected failures',
                 'KFAIL':'known failures',
                 'KPASS':'unknown passes',
                 'UNRESOLVED':'unresolved testcases',
                 'UNTESTED':'untested testcases',
                 'REGRESSED':'runtime performance regression',
                 'IMPROVED':'runtime performance improvement',
                 'UNSUPPORTED':'unsupported tests',
                 'SKIPPED':'skipped tests',
                 'TIMEOUT':'timeout waiting for results',
                 'NOEXE':'test executable is missing'}

  def __init__(self, ignore=[], flaky=[], max_logs=20, parseSummaryOnly=False,
               *args, **kwargs):
    super().__init__(*args, **kwargs)
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
    description = Test.describe(self, done) or list()

    # We use resultNames here so that the printed order is always the same.
    # resultCounts is a dictionary that goes by insertion order instead.
    for resultName, resultDescription in self.resultNames.items():
      count = self.logObserver.resultCounts.get(resultName, 0)
      if count:
        print(">>>> LitLogObserver.describe: description={}".format(description))
        description.append('{0} {1}'.format(count, resultDescription))

    unknown = set(self.logObserver.resultCounts.keys()) - set(self.resultNames.keys())
    for name in unknown:
      description.append('Unexpected test result output ' + name)

    return description
