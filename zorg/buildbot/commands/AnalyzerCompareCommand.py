import sys
import os

from buildbot.steps import shell
from buildbot.status import builder
from buildbot.process import buildstep

class AnalyzerCompareCommand(shell.ShellCommand):
  """Command suitable for displaying a comparison of two static analyzer
  runs, as output by the clang 'utils/analyzer/CmpRun' tool."""

  class Observer(buildstep.LogLineObserver):
    def __init__(self):
      buildstep.LogLineObserver.__init__(self)

      # Counts of various reports.
      self.num_reports = None
      self.num_added = 0
      self.num_removed = 0
      self.num_changed = 0

      # Reports to notify the user about; a list of tuples of (title,
      # name, html-report).
      self.reports = []

      # Lines we couldn't parse.
      self.invalid_lines = []

      # Make sure we get all the data.
      self.setMaxLineLength(sys.maxint)

    def outLineReceived(self, line):
      """This is called once with each line of the test log."""

      # Ignore empty lines.
      line = line.strip()
      if not line:
        return

      # Everything else should be eval()able.
      try:
        data = eval(line)
        key = data[0]
      except:
        self.invalid_lines.append(line)
        return

      # FIXME: Improve error checking.
      if key == 'ADDED':
        _,name,report = data
        self.num_added += 1
        self.reports.append(('added', str(name), str(report)))
      elif key == 'REMOVED':
        _,name,report = data
        self.num_removed += 1
        self.reports.append(('removed', str(name), str(report)))
      elif key == 'CHANGED':
        _,name,old_name,report,old_report = data
        self.num_removed += 1
        self.reports.append(('modified', str(name), str(report)))
      elif key == 'TOTAL':
        if self.num_reports is not None:
          self.invalid_lines.append(line)
          return

        _,count = data
        self.num_reports = count
      else:
        self.invalid_lines.append(line)
        
  def __init__(self, **kwargs):
    shell.ShellCommand.__init__(self, **kwargs)
    self.observer = AnalyzerCompareCommand.Observer()
    self.addLogObserver('comparison-data', self.observer)

  def getText(self, cmd, results):
    basic_info = self.describe(True)
    
    added = self.observer.num_added
    removed = self.observer.num_removed
    changed = self.observer.num_changed
    total = self.observer.num_reports

    if total is not None:
      basic_info.append('%d reports' % total)
    for name,count in (("added", self.observer.num_added),
                       ("removed", self.observer.num_removed),
                       ("changed", self.observer.num_changed)):
      if count:
        basic_info.append('%d %s' % (count, name))

    return basic_info

  def createSummary(self, log):
    # Add the "interesting" reports.
    for title,name,data in self.observer.reports:
      self.addHTMLLog("%s:%s" % (title, os.path.basename(name)), data)

  def evaluateCommand(self, cmd):
    # Always fail if the command itself failed.
    if cmd.rc != 0:
      return builder.FAILURE

    # Warn about added reports.
    if self.observer.num_added:
      return builder.WARNINGS

    return builder.SUCCESS

