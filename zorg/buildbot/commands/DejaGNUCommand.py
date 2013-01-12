import re
import urllib
import buildbot
import buildbot.status.builder
from buildbot.status.results import FAILURE, SUCCESS
import buildbot.steps.shell
from buildbot.process.buildstep import LogLineObserver
from buildbot.steps.shell import Test

class DejaGNULogObserver(LogLineObserver):
    kStartLineRE = re.compile(r'Running .*/(.*/.*\.exp) \.\.\.');
    kFinishLineRE = re.compile(r'testcase .*/(.*/.*\.exp) completed in .* seconds');
    kTestStateLineRE = re.compile(r'(FAIL|PASS|XFAIL|XPASS|KFAIL|KPASS|UNRESOLVED|UNTESTED|UNSUPPORTED): .*')
    failingCodes = set(['FAIL', 'XPASS', 'KPASS', 'UNRESOLVED'])
    def __init__(self):
        LogLineObserver.__init__(self)
        self.resultCounts = {}
        self.currentLines = ''
        self.currentFailed = False
        self.anyFailed = False
    def outLineReceived(self, line):
        if len(self.currentLines):
            self.currentLines += '\n' + line
            m = self.kTestStateLineRE.search(line)
            if m:
                resultCode, = m.groups()
                if resultCode in self.failingCodes:
                    self.hasFailed = True
                    self.currentFailed = True
                    self.anyFailed = True
                if not resultCode in self.resultCounts:
                    self.resultCounts[resultCode] = 0
                self.resultCounts[resultCode] += 1
            m = self.kFinishLineRE.match(line)
            if m:
                name, = m.groups()
                if self.currentFailed:
                    self.step.addCompleteLog(name.replace('/', '__'), self.currentLines)
                self.currentLines = ''
        else:
            m = self.kStartLineRE.match(line)
            if m:
                self.currentLines = line
                self.currentFailed = False

class DejaGNUCommand(Test):
    resultNames = {'FAIL':'unexpected failures',
                   'PASS':'expected passes',
                   'XFAIL':'expected failures',
                   'XPASS':'unexpected passes',
                   'KFAIL':'known failures',
                   'KPASS':'unknown passes',
                   'UNRESOLVED':'unresolved testcases',
                   'UNTESTED':'untested testcases',
                   'UNSUPPORTED':'unsupported tests'}

    def __init__(self, ignore=[], flaky=[], max_logs=20,
                 *args, **kwargs):
        Test.__init__(self, *args, **kwargs)
        self.logObserver = DejaGNULogObserver()
        self.addLogObserver('gdb.log', self.logObserver)

    def evaluateCommand(self, cmd):
        if self.logObserver.anyFailed:
            return FAILURE
        return SUCCESS

    def describe(self, done=False):
        description = Test.describe(self, done)
        for name, count in self.logObserver.resultCounts.iteritems():
            description.append('{0} {1}'.format(count, self.resultNames[name]))
        return description
