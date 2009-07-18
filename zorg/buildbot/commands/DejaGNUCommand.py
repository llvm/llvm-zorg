import re
import buildbot
import buildbot.status.builder
from buildbot.steps.shell import Test

class DejaGNUCommand(Test):
    command=["make", "check"]
    total = 0
    description = "testing llvm"
    descriptionDone = "test llvm"
    def describe(self, done=False):
        result = Test.describe(self, done)
        return result
    def evaluateCommand(self, cmd):
        # FIXME: This doesn't detect failures if dejagnu doesn't run.
        rc = 0
        lines = self.getLog('stdio').readlines()
        failre = re.compile("^FAIL:.*")
        faillines = []
        xpass_result = re.compile("^# of unexpected passes\s*(\d+)")
        xpasses = 0
        xfail_result = re.compile("^# of expected failures\s*(\d+)")
        xfails = 0
        fail_result = re.compile("^# of unexpected failures\s*(\d+)")
        fails = 0
        pass_result = re.compile("^# of expected passes\s*(\d+)")
        passes = 0
        fails_list = []
        for line in lines:
            result = failre.search(line)
            if result:
                faillines.append(line)
            result =  xpass_result.search(line)
            if result:
                xpasses += int(result.group(1))
            result =  xfail_result.search(line)
            if result:
                xfails += int(result.group(1))
            result =  pass_result.search(line)
            if result:
                passes += int(result.group(1))
            result =  fail_result.search(line)
            if result:
                fails += int(result.group(1))
                fails_list.append(line)
        if faillines:
            self.addCompleteLog("fails", "\n".join(faillines) + "\n")
        if fails == 0:
            rc = buildbot.status.builder.SUCCESS
        else:
            rc = buildbot.status.builder.FAILURE
        self.setTestResults(total = fails+xpasses+xfails+passes, 
                            failed = fails, 
                            passed = passes, 
                            warnings = xpasses + xfails)
        return rc
