import itertools
import re
import os

import buildbot
import buildbot.steps.shell

# FIXME: Rename to LitTestCommand.
class ClangTestCommand(buildbot.steps.shell.Test):
  # FIXME: We should process things in a test observer instead of at the end.

  kTestLineRE = re.compile(r'([^ ]*): (.*) \(.*.*\)')
  kTestFailureLogStartRE = re.compile(r"""\*{4,80} TEST '(.*)' .*""")
  kTestFailureLogStopRE = re.compile(r"""\*{10,80}""")

  # Show a maximum of 20 individual failure logs.
  kMaxFailureLogs = 20

  def evaluateCommand(self, cmd):
    rc = 0
    grouped = {}
    failureLogs = []
    lines = self.getLog('stdio').readlines()

    it = iter(lines)
    inFailure = None
    for ln in it:
      # See if we are inside a failure log.
      if inFailure:
        inFailure[1].append(ln)
        if ClangTestCommand.kTestFailureLogStopRE.match(ln):
          failureLogs.append(tuple(inFailure))
          inFailure = None
        continue

      ln = ln.strip()
      if not ln:
        continue

      # Check for test failure logs.
      m = ClangTestCommand.kTestFailureLogStartRE.match(ln)
      if m:
        inFailure = (m.group(1), [ln])
        continue

      # Otherwise expect a test status line.
      m = ClangTestCommand.kTestLineRE.match(ln)
      if m:
        groupName = m.group(1)
        testName = m.group(2)
        if groupName not in grouped:
          grouped[groupName] = []
        grouped[groupName].append(testName)

    if inFailure:
      # FIXME: Different error?
      raise ValueError,"Unexpected clang test running output, unterminated failure log!"

    for name,items in grouped.items():
      if name != 'PASS' and items:
        self.addCompleteLog(name.lower(), '\n'.join(items) + '\n')
    for name,items in failureLogs[:self.kMaxFailureLogs]:
      self.addCompleteLog(os.path.basename(name.lower()),
                          ''.join(items) + '\n')

    numPass = len(grouped.get('PASS',()))
    numFail = len(grouped.get('FAIL',()))
    numXFail = len(grouped.get('XFAIL',()))
    numXPass = len(grouped.get('XPASS',()))
    numUnsupported = len(grouped.get('UNSUPPORTED',()))
    numUnresolved = len(grouped.get('UNRESOLVED',()))
    self.setTestResults(total=numPass + numFail + numXFail + numXPass,
                        failed=numFail + numXPass + numUnresolved,
                        passed=numPass + numXFail,
                        warnings=numXFail)
    if numFail + numXPass + numUnresolved:
      return buildbot.status.builder.FAILURE
    return buildbot.status.builder.SUCCESS
