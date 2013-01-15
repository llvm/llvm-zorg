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
    def __init__(self):
        LogLineObserver.__init__(self)
        self.resultCounts = {}
        self.inFailure = None
    def outLineReceived(self, line):
      # See if we are inside a failure log.
      if self.inFailure:
        self.inFailure[1].append(line)
        if self.kTestFailureLogStopRE.match(line):
          name,log = self.inFailure
          self.step.addCompleteLog(name.replace('/', '__'), '\n'.join(log))
          self.inFailure = None
        return

      line = line.strip()
      if not line:
        return

      # Check for test failure logs.
      m = self.kTestFailureLogStartRE.match(line)
      if m:
        self.inFailure = (m.group(1), [line])
        return

      # Otherwise expect a test status line.
      m = self.kTestLineRE.match(line)
      if m:
        code, name = m.groups()
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
    failingCodes = set(['FAIL', 'XPASS', 'KPASS', 'UNRESOLVED'])

    def __init__(self, ignore=[], flaky=[], max_logs=20,
                 *args, **kwargs):
        Test.__init__(self, *args, **kwargs)
        self.logObserver = LitLogObserver()
        self.addLogObserver('stdio', self.logObserver)

    def evaluateCommand(self, cmd):
        if any([r in self.logObserver.resultCounts for r in self.failingCodes]):
            return FAILURE
        return SUCCESS

    def describe(self, done=False):
        description = Test.describe(self, done)
        for name, count in self.logObserver.resultCounts.iteritems():
            description.append('{0} {1}'.format(count, self.resultNames[name]))
        return description
