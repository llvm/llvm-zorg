#!/usr/bin/python
# Copyright (c) 2006-2008 The Chromium Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE.chromium.TXT file.

"""A buildbot command for running and interpreting GTest tests."""

import re
from buildbot.steps import shell
from buildbot.status import builder
from buildbot.process import buildstep

class TestObserver(buildstep.LogLineObserver):
  """This class knows how to understand GTest test output."""

  def __init__(self):
    buildstep.LogLineObserver.__init__(self)

    # State tracking for log parsing
    self._current_test_case = ''
    self._current_test = ''
    self._current_failure = None
    self._suites_started = 0
    self._suites_ended = 0

    # This may be either text or a number. It will be used in the phrase
    # '%s disabled' on the waterfall display.
    self.disabled_tests = 0

    # Failures are stored here as 'test name': [failure description]
    self.failed_tests = {}

    # Regular expressions for parsing GTest logs
    self._test_case_start = re.compile('\[----------\] \d+ tests? from (\w+)')
    self._test_start = re.compile('^\[ RUN      \] .+\.(\w+)')
    self._test_end   = re.compile('^^\[(       OK |  FAILED  )] .+\.(\w+)')
    self._disabled   = re.compile('  YOU HAVE (\d+) DISABLED TEST')
    self._suite_start = re.compile(
        '^\[==========\] Running \d+ tests? from \d+ test cases?.')
    self._suite_end  = re.compile(
        '^\[==========\] \d+ tests? from \d+ test cases? ran.')

  def RunningTests(self):
    """Returns True if we appear to be in the middle of running tests."""
    return self._suites_started > self._suites_ended

  def outLineReceived(self, line):
    """This is called once with each line of the test log."""

    # Is it the first line of the suite?
    results = self._suite_start.search(line)
    if results:
      self._suites_started += 1
      return

    # Is it a line reporting disabled tests?
    results = self._disabled.search(line)
    if results:
      try:
        disabled = int(results.group(1))
      except ValueError:
        disabled = 0
      if disabled > 0 and isinstance(self.disabled_tests, int):
        self.disabled_tests += disabled
      else:
        # If we can't parse the line, at least give a heads-up. This is a
        # safety net for a case that shouldn't happen but isn't a fatal error.
        self.disabled_tests = 'some'
      return

    # We don't care about anything else if we're not in the list of tests.
    if not self.RunningTests():
      return

    # Is it the first line in a test case?
    results = self._test_case_start.search(line)
    if results:
      self._current_test = ''
      self._failure_description = []
      self._current_test_case = results.group(1)
      return

    # Is it the last line of the suite (if so, clear state)?
    results = self._suite_end.search(line)
    if results:
      self._suites_ended += 1
      self._current_test_case = ''
      self._current_test = ''
      self._failure_description = []
      return

    # Is it the start of an individual test?
    results = self._test_start.search(line)
    if results:
      self._current_test = results.group(1)
      test_name = '.'.join([self._current_test_case, self._current_test])
      self._failure_description = ['%s:' % test_name]
      return

    # Is it a test result line?
    results = self._test_end.search(line)
    if results:
      if results.group(1) == '  FAILED  ':
        test_name = '.'.join([self._current_test_case, self._current_test])
        self.failed_tests[test_name] = self._failure_description
      self._current_test = ''
      self._failure_description = []

    # Random line: if we're in a test, collect it for the failure description.
    if self._current_test:
      self._failure_description.append(line)


class GTestCommand(shell.ShellCommand):
  """Buildbot command that knows how to display GTest output."""

  def __init__(self, **kwargs):
    shell.ShellCommand.__init__(self, **kwargs)
    self.test_observer = TestObserver()
    self.addLogObserver('stdio', self.test_observer)

  def getText(self, cmd, results):
    basic_info = self.describe(True)
    disabled = self.test_observer.disabled_tests
    if disabled:
      basic_info.append('%s disabled' % str(disabled))

    if results == builder.SUCCESS:
      return basic_info
    elif results == builder.WARNINGS:
      return basic_info + ['warnings']

    if self.test_observer.RunningTests():
      basic_info += ['did not complete']

    if len(self.test_observer.failed_tests) > 0:
      failure_text = ['failed %d' % len(self.test_observer.failed_tests)]
    else:
      failure_text = ['crashed or hung']
    return basic_info + failure_text

  def _TestAbbrFromTestID(self, id):
    """Split the test's individual name from GTest's full identifier.
    The name is assumed to be everything after the final '.', if any.
    """
    return id.split('.')[-1]

  def createSummary(self, log):
    observer = self.test_observer
    if observer.failed_tests:
      for failure in observer.failed_tests:
        # GTest test identifiers are of the form TestCase.TestName. We display
        # the test names only.  Unfortunately, addCompleteLog uses the name as
        # both link text and part of the text file name, so we can't incude
        # HTML tags such as <abbr> in it.
        self.addCompleteLog(self._TestAbbrFromTestID(failure),
                            '\n'.join(observer.failed_tests[failure]))

