import re
import urllib
import buildbot
import buildbot.status.builder
import buildbot.steps.shell

class StandardizedTest(buildbot.steps.shell.Test):
    # FIXME: We should process things in a test observer instead of at the end.

    knownCodes = ['FAIL', 'XFAIL', 'PASS', 'XPASS',
                  'UNRESOLVED', 'UNSUPPORTED', 'IMPROVED', 'REGRESSED']
    failingCodes = set(['FAIL', 'XPASS', 'UNRESOLVED'])
    warningCodes = set(['IGNORE PASS', 'IGNORE XFAIL', 'REGRESSED'])

    # The list of all possible codes, including flaky and ignored codes. This is
    # the display order, as well.
    allKnownCodes = (knownCodes + ['IGNORE ' + c for c in knownCodes] +
                     ['FLAKY ' + c for c in knownCodes])

    testLogName = 'stdio'

    def __init__(self, ignore=[], flaky=[], max_logs=20,
                 *args, **kwargs):
        buildbot.steps.shell.Test.__init__(self, *args, **kwargs)

        self.flakyTests = set(flaky)
        self.ignoredTests = set(ignore)
        self.maxLogs = int(max_logs)
        self.addFactoryArguments(flaky=list(flaky))
        self.addFactoryArguments(ignore=list(ignore))
        self.addFactoryArguments(max_logs=max_logs)

    def parseLog(self, log_lines):
        """parseLog(log_lines) -> [(result_code, test_name, test_log), ...]"""
        raise RuntimeError("Abstract method.")

    def evaluateCommand(self, cmd):
        results_by_code = {}
        logs = []
        lines = self.getLog(self.testLogName).readlines()
        hasIgnored = False
        for result,test,log in self.parseLog(lines):
            test = test.strip()
            if result not in self.allKnownCodes:
                raise ValueError,'test command return invalid result code!'

            # Convert codes for flaky and ignored tests.
            if test in self.flakyTests:
                result = 'FLAKY ' + result
            elif test in self.ignoredTests:
                result = 'IGNORE ' + result

            if result.startswith('FLAKY ') or result.startswith('IGNORE '):
                hasIgnored = True
                

            results_by_code.setdefault(result, []).append(test)

            # Add logs for failures.
            if result in self.failingCodes and len(logs) < self.maxLogs:
                if log is not None and log.strip():
                    # Buildbot 0.8 doesn't properly quote slashes, replace them.
                    test = test.replace("/", "___")
                    logs.append((test, log))

        # Explicitly remove any ignored warnings for tests which are
        # also in the an ignored failing set (some tests may appear
        # twice).
        ignored_failures = set()
        for code in self.failingCodes:
            results = results_by_code.get('IGNORE ' + code)
            if results:
                ignored_failures |= set(results)
        for code in self.warningCodes:
            results = results_by_code.get(code)
            if results:
                results_by_code[code] = [x for x in results_by_code[code]
                                         if x not in ignored_failures]

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
                results.sort()
                self.addCompleteLog('tests.%s' % code,
                                    '\n'.join(results) + '\n')

        self.setTestResults(total=total, failed=failed,
                            passed=passed, warnings=warnings)

        # Add the logs.
        logs.sort()
        for test, log in logs:
            self.addCompleteLog(test, log)

        # Always fail if the command itself failed, unless we have ignored some
        # test results (which presumably would have caused the actual test
        # runner to fail).
        if not hasIgnored and cmd.rc != 0:
            return buildbot.status.builder.FAILURE

        # Report failure/warnings beased on the test status.
        if failed:
            return buildbot.status.builder.FAILURE
        if warnings:
            return buildbot.status.builder.WARNINGS

        return buildbot.status.builder.SUCCESS
