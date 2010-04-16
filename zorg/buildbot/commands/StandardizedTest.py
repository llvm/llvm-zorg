import re
import buildbot
import buildbot.status.builder
import buildbot.steps.shell

class StandardizedTest(buildbot.steps.shell.Test):
    # FIXME: We should process things in a test observer instead of at the end.

    knownCodes = ['FAIL', 'XFAIL', 'PASS', 'XPASS',
                  'UNRESOLVED', 'UNSUPPORTED']
    failingCodes = set(['FAIL', 'XPASS', 'UNRESOLVED'])
    warningCodes = set(['IGN PASS', 'IGN XFAIL'])

    # The list of all possible codes, including ignored codes. This is the
    # display order, as well.
    allKnownCodes = knownCodes + ['IGN ' + c for c in knownCodes]

    testLogName = 'stdio'

    def __init__(self, ignore=[], max_logs=20,
                 *args, **kwargs):
        buildbot.steps.shell.Test.__init__(self, *args, **kwargs)

        self.ignoredTests = set(ignore)
        self.maxLogs = int(max_logs)
        self.addFactoryArguments(ignore=list(ignore))
        self.addFactoryArguments(max_logs=max_logs)

    def parseLog(self, log_lines):
        """parseLog(log_lines) -> [(result_code, test_name, test_log), ...]"""
        abstract

    def evaluateCommand(self, cmd):
        # Always fail if the command itself failed.
        if cmd.rc != 0:
            return buildbot.status.builder.FAILURE

        results_by_code = {}
        logs = []
        lines = self.getLog(self.testLogName).readlines()
        for result,test,log in self.parseLog(lines):
            if result not in self.knownCodes:
                raise ValueError,'test command return invalid result code!'

            # Convert externally expected failures.
            if test in self.ignoredTests:
                result = 'IGN ' + result

            if result not in results_by_code:
                results_by_code[result] = set()

            results_by_code[result].add(test)

            # Add logs for failures.
            if result in self.failingCodes and len(logs) < self.maxLogs:
                if log is not None and log.strip():
                    logs.append((test, log))

        # Summarize result counts.
        total = failed = passed = warnings = 0
        for code in self.allKnownCodes:
            results = results_by_code.get(code)
            if not results:
                continue

            total += len(results)
            if code in self.failingCodes:
                failed += len(results)
            elif code in self.warningCodes:
                warnings += len(results)
            else:
                passed += len(results)

            # Add a list of the tests in each category, for everything except
            # PASS.
            if code != 'PASS':
                results = list(results)
                results.sort()
                self.addCompleteLog('tests.%s' % code,
                                    '\n'.join(results) + '\n')

        self.setTestResults(total=total, failed=failed,
                            passed=passed, warnings=warnings)

        # Add the logs.
        logs.sort()
        for test, log in logs:
            self.addCompleteLog(test, log)

        if failed:
            return buildbot.status.builder.FAILURE
        if warnings:
            return buildbot.status.builder.WARNINGS

        return buildbot.status.builder.SUCCESS
