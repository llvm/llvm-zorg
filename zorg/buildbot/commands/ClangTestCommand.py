import itertools
import re

import buildbot
import buildbot.steps.shell

class ClangTestCommand(buildbot.steps.shell.Test):
  description = "testing clang"
  descriptionDone = "test clang"
  kTestLineRE = re.compile(r'([^ ]*): (.*) \(.*.*\)')
  def evaluateCommand(self, cmd):
    rc = 0
    grouped = {}
    failureLog = []
    lines = self.getLog('stdio').readlines()

    it = iter(lines)
    for ln in it:
      ln = ln.strip()
      if not ln:
        continue
      
      m = ClangTestCommand.kTestLineRE.match(ln)
      if m:
        groupName = m.group(1)
        testName = m.group(2)
        if groupName not in grouped:
          grouped[groupName] = []
        grouped[groupName].append(testName)

    # FIXME: Get logs for failures.
    for name,items in grouped.items():
      if name != 'PASS' and items:
        self.addCompleteLog(name.lower(), '\n'.join(items) + '\n')
    numPass = len(grouped.get('PASS',()))
    numFail = len(grouped.get('FAIL',()))
    numXFail = len(grouped.get('XFAIL',()))
    numXPass = len(grouped.get('XPASS',()))
    self.setTestResults(total=numPass + numFail + numXFail + numXPass, 
                        failed=numFail + numXPass, 
                        passed=numPass + numXFail, 
                        warnings=numXFail)
    if numFail + numXPass:
      return buildbot.status.builder.FAILURE
    return buildbot.status.builder.SUCCESS
