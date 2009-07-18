import itertools
import re

import buildbot
import buildbot.steps.shell

class ClangTestCommand(buildbot.steps.shell.Test):
  description = "testing clang"
  descriptionDone = "test clang"
  kFailRE = re.compile(r"[*]+ TEST '(.*)' FAILED! [*]+")
  kXFailRE = re.compile(r"XFAILED '(.*)': (.*)")
  kMakeLineRE = re.compile(r"make([[].*[]])?: .*")
  def evaluateCommand(self, cmd):
    rc = 0
    fails = []
    passes = []
    xfails = []
    xpasses = []
    failureLog = []
    lines = self.getLog('stdio').readlines()

    # Trim lame startup message.
    if lines[0].startswith('--- Running'):
      lines = lines[1:]

    it = iter(lines)
    for ln in it:
      ln = ln.strip()
      if not ln:
        continue
      
      # Strip make information.
      if ClangTestCommand.kMakeLineRE.match(ln):
        continue

      m = ClangTestCommand.kFailRE.match(ln)
      if m:
        # Found a failure, pull out the log.
        failLn = ln
        testName = m.group(1)
        fails.append(testName)
        self.readFailData(testName, it, failureLog)
        continue
      
      # Grumble. Current stuff never prints XFAILS except when they
      # pass. Lame.
      m = ClangTestCommand.kXFailRE.match(ln)
      if m:
        testName,xfailReason = m.groups()

        # Look for failure log.
        try:
          ln = it.next().strip()
        except StopIteration:
          ln = None
        
        if ln is not None:
          m = ClangTestCommand.kFailRE.match(ln)
          if m:
            # Read off failure log.
            self.readFailData(testName, it, failureLog)
          else:
            # Something else, push the line back.
            it = itertools.chain(iter([ln]), it)

        # FIXME: Make test output less sucky so we can count XFAILs.
        xpasses.append(testName)
        continue

      passes.append(ln)
    if fails:
      self.addCompleteLog("fails", "\n".join(fails) + "\n")
    if xfails:
      self.addCompleteLog("xfails", "\n".join(xfails) + "\n")
    if 0:
      self.addCompleteLog("passes", "\n".join(passes) + "\n")
    if failureLog:
      self.addCompleteLog("failure log", "".join(failureLog) + "\n")
    self.setTestResults(total=len(passes) + len(fails) + len(xfails) + len(xpasses), 
                        failed=len(fails) + len(xpasses), 
                        passed=len(passes) + len(xfails), 
                        warnings=len(xfails))
    if fails:
      return buildbot.status.builder.FAILURE
    return buildbot.status.builder.SUCCESS

  def readFailData(self, name, it, log):
    # Read off the failure log.
    log.append("FAIL: %s\n" % name)
    for ln in it:
      m = ClangTestCommand.kFailRE.match(ln)
      if m:
        break
      else:
        log.append(ln)
    log.append("\n")
