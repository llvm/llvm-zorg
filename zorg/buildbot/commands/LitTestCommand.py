import re
import StandardizedTest

class LitTestCommand(StandardizedTest.StandardizedTest):
  kTestLineRE = re.compile(r'([^ ]*): (.*) \(.*.*\)')
  kTestFailureLogStartRE = re.compile(r"""\*{4,80} TEST '(.*)' .*""")
  kTestFailureLogStopRE = re.compile(r"""\*{10,80}""")

  def parseLog(self, lines):
    results = []
    results_by_name = {}
    failureLogs = []
    lines = self.getLog('stdio').readlines()

    it = iter(lines)
    inFailure = None
    for ln in it:
      # See if we are inside a failure log.
      if inFailure:
        inFailure[1].append(ln)
        if self.kTestFailureLogStopRE.match(ln):
          name,log = inFailure
          if name not in results_by_name:
            raise ValueError,'Invalid log result with no status line!'
          results_by_name[name][2] = ''.join(log) + '\n'
          inFailure = None
        continue

      ln = ln.strip()
      if not ln:
        continue

      # Check for test failure logs.
      m = self.kTestFailureLogStartRE.match(ln)
      if m:
        inFailure = (m.group(1), [ln])
        continue

      # Otherwise expect a test status line.
      m = self.kTestLineRE.match(ln)
      if m:
        code, name = m.group(1),m.group(2)
        results.append( [code, name, None] )
        results_by_name[name] = results[-1]

    if inFailure:
      raise ValueError,("Unexpected clang test running output, "
                        "unterminated failure log!")

    return results
