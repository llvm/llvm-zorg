# pylint: disable=C0103

"""This class knows how to understand annotations.

    Here are a list of the currently supported annotations:

    @@@BUILD_STEP <stepname>@@@
    Add a new step <stepname>. End the current step, marking with last available
    status.

    @@@STEP_LINK@<label>@<url>@@@
    Add a link with label <label> linking to <url> to the current stage.

    @@@STEP_WARNINGS@@@
    Mark the current step as having warnings (oragnge).

    @@@STEP_FAILURE@@@
    Mark the current step as having failed (red).

    @@@STEP_EXCEPTION@@@
    Mark the current step as having exceptions (magenta).

    @@@STEP_CLEAR@@@
    Reset the text description of the current step.

    @@@STEP_SUMMARY_CLEAR@@@
    Reset the text summary of the current step.

    @@@STEP_TEXT@<msg>@@@
    Append <msg> to the current step text.

    @@@STEP_SUMMARY_TEXT@<msg>@@@
    Append <msg> to the step summary (appears on top of the waterfall).

    @@@HALT_ON_FAILURE@@@
    Halt if exception or failure steps are encountered (default is not).

    @@@HONOR_ZERO_RETURN_CODE@@@
    Honor the return code being zero (success), even if steps have other results.

    Deprecated annotations:
    TODO(bradnelson): drop these when all users have been tracked down.

    @@@BUILD_WARNINGS@@@
    Equivalent to @@@STEP_WARNINGS@@@

    @@@BUILD_FAILED@@@
    Equivalent to @@@STEP_FAILURE@@@

    @@@BUILD_EXCEPTION@@@
    Equivalent to @@@STEP_EXCEPTION@@@

    @@@link@<label>@<url>@@@
    Equivalent to @@@STEP_LINK@<label>@<url>@@@
"""

import re

from twisted.internet import defer
from twisted.internet import error
from twisted.python import failure
from twisted.python import log as logging

from buildbot.process import buildstep
from buildbot.process import results
from buildbot.process import logobserver

from buildbot.plugins import util

from buildbot.util import asyncSleep
from buildbot.util.misc import deferredLocked

if False:  # for debugging
    debuglog = logging.msg
else:
    debuglog = lambda m: None

class AnnotatedBuildStep(buildstep.BuildStep):

    def  __init__(self, parent_step, *args, **kwargs):
        self.parent_step = parent_step
        buildstep.BuildStep.__init__(self, *args, **kwargs)

        # Step is really unpredictable
        self.useProgress = False

        self.build = self.parent_step.build
        self.master = self.parent_step.build.master
        self.worker = self.parent_step.worker

        self.stdio_log = None

        self._loglines = []
        self._logLock = defer.DeferredLock()

        self._request_finish = False

    @defer.inlineCallbacks
    def addStep(self):
        debuglog("AnnotatedBuildStep: adding step '%s': buildid=%s" % (
                    self.name, self.build.buildid))
        yield buildstep.BuildStep.addStep(self)
        # Put ourselves into a list of processed steps of the build object.
        self.build.executedSteps.append(self)
        # Init result to SUCCESS by default.
        self.results = results.SUCCESS
        self.description = [self.name]
        self.stdio_log = yield self.addLog('stdio')

        debuglog("AnnotatedBuildStep: added step '%s': stepid=%s, buildid=%s" % (
                    self.name, self.stepid, self.build.buildid))


    @defer.inlineCallbacks
    def finishStep(self):
        hidden = False
        debuglog("AnnotatedBuildStep: finish step '%s': stepid=%s, buildid=%s, results=%s" % (
                    self.name, self.stepid, self.build.buildid, self.results))
        yield self.master.data.updates.finishStep(self.stepid, self.results,
                                                  hidden)
        # finish unfinished logs
        yield self.finishUnfinishedLogs()

    @defer.inlineCallbacks
    def startStep(self, remote, done=False):
        debuglog("AnnotatedBuildStep::startStep() starting '%s': "
                 "buildid=%s, done=%s" % (
                 self.name, self.build.buildid, done))

        try:
            yield self.addStep()

            try:
                self.realUpdateSummary()
                # The "main" step has finished already.
                # Do only necessary work.
                #NOTE: we can get 'request finish' flag before the step started.
                self._request_finish = self._request_finish or done
                self._running = True
                self.results = yield self.run()
            finally:
                self._running = False

        except buildstep.BuildStepCancelled:
            self.results = results.CANCELLED

        except buildstep.BuildStepFailed:
            self.results = results.FAILURE

        except error.ConnectionLost:
            self.results = results.RETRY

        except Exception:
            self.results = results.EXCEPTION
            why = failure.Failure()
            logging.err(why, "AnnotatedBuildStep.failed; traceback follows")
            yield self.addLogWithFailure(why)

        finally:
            # update the summary one last time, make sure that completes,
            # and then don't update it any more.
            self.realUpdateSummary()
            yield self.realUpdateSummary.stop()

            # Update step status in the database.
            yield self.finishStep()

        debuglog("AnnotatedBuildStep::startStep() completed '%s': "
                 "stepid=%s, buildid=%s, results=%s" % (
                 self.name, self.stepid, self.build.buildid, self.results))

    def requestFinish(self, status=None):
        debuglog("AnnotatedBuildStep::requestFinish(%r): '%s': "
                 "stepid=%s, buildid=%s, results=%r" % (
                 status, self.name, self.stepid, self.build.buildid, self.results))
        # Update the current step status with the worst result.
        if status is not None:
            self.updateStatus(status)
        self._request_finish = True

    def setStepText(self, text=None):
        if text is not None:
            if self.description is not None:
                self.description.append(text)
        else:
            self.description = []

        self.updateSummary()

    def setStepSummary(self, text=None):
        if text is not None:
            if self.descriptionDone is not None:
                self.descriptionDone.append(text)
        else:
            self.descriptionDone = []

        self.updateSummary()

    @deferredLocked("_logLock")
    def _flushLogs(self):
        if self._loglines:
            ll = "".join(self._loglines)
            self._loglines = []
            self.stdio_log.addStdout(ll)
        return defer.succeed(None)

    @deferredLocked("_logLock")
    def _addLogs(self, text):
        if text is not None:
            self._loglines.append(text)
        return defer.succeed(None)

    @defer.inlineCallbacks
    def run(self):
        debuglog("AnnotatedBuildStep::run() starting '%s' step: "
                 "stepid=%s, buildid=%s" % (
                 self.name, self.stepid, self.build.buildid))

        # Save previously collected log lines.
        yield self._flushLogs()

        while not self._request_finish:
            # Sleep for .1 second. Let arrive more logs.
            yield asyncSleep(.1)
            if self._loglines:
                yield self._flushLogs()

        # and the last one time.
        if self._loglines:
            yield self._flushLogs()

        debuglog("AnnotatedBuildStep::run() exiting '%s' step: "
                 "stepid=%s, buildid=%s, results=%s" % (
                 self.name, self.stepid, self.build.buildid, self.results))

        return self.results

    @defer.inlineCallbacks
    def scheduleStdout(self, text):
        if text is None:
            return

        # Not running yet, just store a log line.
        if not self._running:
            self._loglines.append(text)
            return

        # Already executed, add the log line with locking.
        yield self._addLogs(text=text)

    def updateStatus(self, status):
        self.results = results.worst_status(self.results, status)


ALL_COMMANDS = list(range(11))
STEP_LINK, STEP_WARNINGS, STEP_FAILURE, STEP_EXCEPTION, HALT_ON_FAILURE, HONOR_ZERO_RC, STEP_CLEAR, STEP_SUMMARY_CLEAR, STEP_TEXT, STEP_SUMMARY_TEXT, BUILD_STEP = ALL_COMMANDS

class AnnotatedCommand(buildstep.ShellMixin, buildstep.BuildStep):
    """Buildbot command that knows how to display annotations."""

    _re_step_link           = re.compile(r'^@@@(STEP_LINK|link)@(?P<link_label>.*)@(?P<link_url>.*)@@@', re.M)
    _re_step_warnings       = re.compile(r'^@@@(STEP_WARNINGS|BUILD_WARNINGS)@@@', re.M)
    _re_step_failure        = re.compile(r'^@@@(STEP_FAILURE|BUILD_FAILED)@@@', re.M)
    _re_step_exception      = re.compile(r'^@@@(STEP_EXCEPTION|BUILD_EXCEPTION)@@@', re.M)
    _re_halt_on_failure     = re.compile(r'^@@@HALT_ON_FAILURE@@@', re.M)
    _re_honor_zero_rc       = re.compile(r'^@@@HONOR_ZERO_RETURN_CODE@@@', re.M)
    _re_step_clear          = re.compile(r'^@@@STEP_CLEAR@@@', re.M)
    _re_step_summary_clear  = re.compile(r'^@@@STEP_SUMMARY_CLEAR@@@', re.M)
    _re_step_text           = re.compile(r'^@@@STEP_TEXT@(?P<text>.*)@@@', re.M)
    _re_step_summary_step   = re.compile(r'^@@@STEP_SUMMARY_TEXT@(?P<text>.*)@@@', re.M)
    _re_build_step          = re.compile(r'^@@@BUILD_STEP (?P<name>.*)@@@', re.M)

    _re_set = [
        # Support: @@@STEP_LINK@<name>@<url>@@@ (emit link)
        # Also support depreceated @@@link@<name>@<url>@@@
        ( STEP_LINK,            _re_step_link),

        # Support: @@@STEP_WARNINGS@@@ (warn on a stage)
        # Also support deprecated @@@BUILD_WARNINGS@@@
        ( STEP_WARNINGS,        _re_step_warnings ),

        # Support: @@@STEP_FAILURE@@@ (fail a stage)
        # Also support deprecated @@@BUILD_FAILED@@@
        ( STEP_FAILURE,         _re_step_failure ),

        # Support: @@@STEP_EXCEPTION@@@ (exception on a stage)
        # Also support deprecated @@@BUILD_FAILED@@@
        ( STEP_EXCEPTION,       _re_step_exception ),

        # Support: @@@HALT_ON_FAILURE@@@ (halt if a step fails immediately)
        ( HALT_ON_FAILURE,      _re_halt_on_failure ),

        # Support: @@@HONOR_ZERO_RETURN_CODE@@@ (succeed on 0 return, even if some
        # steps have failed)
        ( HONOR_ZERO_RC,        _re_honor_zero_rc ),

        # Support: @@@STEP_CLEAR@@@ (reset step description)
        ( STEP_CLEAR,           _re_step_clear ),

        # Support: @@@STEP_SUMMARY_CLEAR@@@ (reset step summary)
        ( STEP_SUMMARY_CLEAR,   _re_step_summary_clear ),

        # Support: @@@STEP_TEXT@<msg>@@@
        ( STEP_TEXT,            _re_step_text ),

        # Support: @@@STEP_SUMMARY_TEXT@<msg>@@@
        ( STEP_SUMMARY_TEXT,    _re_step_summary_step ),

        # Support: @@@BUILD_STEP <step_name>@@@ (start a new section)
        ( BUILD_STEP,           _re_build_step ),
    ]

    def __init__(self, **kwargs):
        # Inject standard tags into the environment.
        env = {
            'BUILDBOT_BLAMELIST':       util.Interpolate('%(prop:blamelist:-[])s'),
            'BUILDBOT_BRANCH':          util.Interpolate('%(prop:branch:-None)s'),
            'BUILDBOT_BUILDERNAME':     util.Interpolate('%(prop:buildername:-None)s'),
            'BUILDBOT_BUILDNUMBER':     util.Interpolate('%(prop:buildnumber:-None)s'),
            'BUILDBOT_CLOBBER':         util.Interpolate('%(prop:clobber:+1)s'),
            'BUILDBOT_GOT_REVISION':    util.Interpolate('%(prop:got_revision:-None)s'),
            'BUILDBOT_REVISION':        util.Interpolate('%(prop:revision:-None)s'),
            'BUILDBOT_SCHEDULER':       util.Interpolate('%(prop:scheduler:-None)s'),
            'BUILDBOT_SLAVENAME':       util.Interpolate('%(prop:slavename:-None)s'),
            'BUILDBOT_MSAN_ORIGINS':    util.Interpolate('%(prop:msan_origins:-)s'),
        }
        # Apply the passed in environment on top.
        old_env = kwargs.get('env') or {}
        env.update(old_env)
        # Change passed in args (ok as a copy is made internally).
        kwargs['env'] = env

        kwargs = self.setupShellMixin(kwargs)
        super().__init__(**kwargs)

        self.addLogObserver('stdio', logobserver.LineConsumerLogObserver(self.processAnnotations))
        # A step log to store all logs, which we got before the first @@@BUILD_STEP @@@ command.
        self.preamble_log = None

        self.annotate_status = results.SUCCESS
        self.halt_on_failure = False
        self.honor_zero_return_code = False

        self.annotated_steps = []
        # Use this lock to "run" the annotated steps.
        self.initLock = defer.DeferredLock()
        self._annotated_finished = False

    def _getLastAnnotatedStep(self):
        return self.annotated_steps[-1] if self.annotated_steps else None

    def _updateLastAnnotatedStepStatus(self, status):
        debuglog(">>> AnnotatedCommand::_updateLastAnnotatedStepStatus(%r)" % status)

        # Alway update the common annotate command status.
        self.annotate_status = results.worst_status(self.annotate_status, status)

        s = self._getLastAnnotatedStep()
        if s is not None:
            s.updateStatus(status)

        if self.halt_on_failure and status in [results.FAILURE, results.EXCEPTION]:
            if self.cmd:
                self.cmd.interrupt("Failed annotated step")

    def _updateLastAnnotatedStepText(self, text = None):
        """Updating a step text. None to clean up."""
        debuglog(">>> AnnotatedCommand::_updateLastAnnotatedStepText('%s')" % (text if text else ''))

        s = self._getLastAnnotatedStep()
        if s is not None:
            s.setStepText(text)

    def _updateLastAnnotatedStepSummaryInfo(self, text = None):
        """Updating a step summary info. None to clean up."""
        debuglog(">>> AnnotatedCommand::_updateLastAnnotatedStepSummaryInfo('%s')" % (text if text else ''))

        s = self._getLastAnnotatedStep()
        if s is not None:
            s.setStepSummary(text)

    def _fixupActiveAnnotatedStep(self):
        debuglog(">>> AnnotatedCommand::_fixupActiveAnnotatedStep()")
        # Fixup the active step
        s = self._getLastAnnotatedStep()
        if s is not None:
            # Finish the active step with its current status.
            s.requestFinish()

    def _scheduleNewAnnotatedStep(self, name, logline):
        debuglog(">>> AnnotatedCommand::_scheduleNewAnnotatedStep('%s')" % name)

        self._fixupActiveAnnotatedStep()

        s = AnnotatedBuildStep(parent_step=self, name=name)
        # Doing this last so that @@@BUILD_STEP... occurs in the log of the new
        # step.
        s.scheduleStdout(logline)
        # Make it ready to consume the logs and status updates.
        self.annotated_steps.append(s)


    @deferredLocked("initLock")
    @defer.inlineCallbacks
    def _execStep(self, step, done):
        yield step.startStep(remote=None, done=done)

    @defer.inlineCallbacks
    def _walkOverScheduledAnnotatedSteps(self):
        debuglog(">>> AnnotatedCommand::_walkOverScheduledAnnotatedSteps: started")

        while self.annotated_steps or not self._annotated_finished:
            if self.annotated_steps:
                yield self._execStep(self.annotated_steps[0], done=self._annotated_finished)
                last_step = self.annotated_steps.pop(0)
                if last_step.results == results.EXCEPTION:
                    raise Exception("Annotated step exception")

            if not self._annotated_finished:
                yield asyncSleep(.1)

        debuglog(">>> AnnotatedCommand::_walkOverScheduledAnnotatedSteps: finished")

    def run(self):
        return self.runAnnotatedCommands()

    @defer.inlineCallbacks
    def runAnnotatedCommands(self):
        try:
            # Create a preamble log for primary annotate step.
            self.preamble_log = yield self.addLog('preamble')

            cmd = yield self.makeRemoteShellCommand(command=self.command,
                                                    stdioLogName='stdio')

            d1 = self.runCommand(cmd)
            d2 = defer.maybeDeferred(self._walkOverScheduledAnnotatedSteps)

            @d1.addBoth
            def cb(r):
                self._annotated_finished = True
                try:
                    # In some cases we can get the empty queue after the check.
                    # Just catch and pass the exception.
                    if self.annotated_steps:
                        # Current processing step.
                        last_step = self.annotated_steps[0]
                        cmd_results = cmd.results()
                        # We can get CANCELLED for two cases:
                        # 1. when UI stop button was pressed. In that case just pass this status
                        #    into the annotated step as the result status.
                        # 2. and when the remote command was canceled because of failed annotated step.
                        #    For that situation we finish the annotated step with its current status.
                        if cmd_results == results.CANCELLED and last_step.results in [results.FAILURE, results.EXCEPTION]:
                            # Finish the annotated step with its current status.
                            last_step.requestFinish()
                        else:
                            last_step.requestFinish(cmd_results)
                except IndexError:
                    pass
                return r

            @d2.addErrback
            def cbErrback(r):
                debuglog("+++ AnnotatedCommand::runAnnotatedCommands(): error callback with exception. "
                         "Terminate remote command.")
                self.annotate_status = results.EXCEPTION
                if self.cmd:
                    self.cmd.interrupt("Annotated step exception")
                return r

            # Wait until both -- the remote command and the annotated step processing loop -- get finished.
            yield defer.DeferredList([d1, d2])

        except Exception:
            why = failure.Failure()
            logging.err(why, "AnnotatedCommand.failed; traceback follows")
            yield self.addLogWithFailure(why)

        # This case when the remote command has been canceled by failed annotated command.
        if cmd.results() == results.CANCELLED and self.annotate_status in [results.FAILURE, results.EXCEPTION]:
            return self.annotate_status
        # Regular case.
        return results.worst_status(cmd.results(), self.annotate_status)

    def processAnnotations(self):

        while True:
            try:
                stream, ln = yield
                # Add \n if not there, which seems to be the case for log lines from
                # windows agents, but not others.
                if not ln.endswith('\n'):
                    ln += '\n'

                self.processAnnotatedCommand(ln)
            except GeneratorExit:
                return

    def processAnnotatedCommand(self, line):
        #pylint: disable=too-many-branches

        # returns: op, args
        def parse_annotate_cmd(ln):
            for ancmd, anre in AnnotatedCommand._re_set:
                ro = anre.search(ln)
                if ro is not None:
                    # Get the regex named group values.
                    # We can get the empty set, but it is ok.
                    args = ro.groupdict() or {}
                    # Store the current log line within the arguments.
                    # We will need to save it in some cases.
                    args['logline'] = ln
                    return ancmd, args
            return None, None

        ancmd, args = parse_annotate_cmd(line)

        if ancmd:
            debuglog(">>> AnnotatedCommand::processAnnotatedCommand(): %s, %r" % (ancmd, args))

        try:
            if ancmd == STEP_LINK:
                s = self._getLastAnnotatedStep()
                if s is not None:
                    s.addURL(args['link_label'], args['link_url'])
                else:
                    logging.msg("Warning: missed link for annotated step. "
                                "No active steps. (%s/%s)" % (args['link_label'], args['link_url']))

            elif ancmd == STEP_WARNINGS:
                self._updateLastAnnotatedStepStatus(results.WARNINGS)
            elif ancmd == STEP_FAILURE:
                self._updateLastAnnotatedStepStatus(results.FAILURE)
            elif ancmd == STEP_EXCEPTION:
                self._updateLastAnnotatedStepStatus(results.EXCEPTION)
            elif ancmd == HALT_ON_FAILURE:
                self.halt_on_failure = True
            elif ancmd == HONOR_ZERO_RC:
                self.honor_zero_return_code = True
            elif ancmd == STEP_CLEAR:
                self._updateLastAnnotatedStepText()
            elif ancmd == STEP_SUMMARY_CLEAR:
                self._updateLastAnnotatedStepSummaryInfo()
            elif ancmd == STEP_TEXT:
                self._updateLastAnnotatedStepText(text=args['text'])
            elif ancmd == STEP_SUMMARY_TEXT:
                self._updateLastAnnotatedStepSummaryInfo(text=args['text'])
            elif ancmd == BUILD_STEP:
                self._scheduleNewAnnotatedStep(name=args['name'].strip(),
                                               logline=args['logline'])
            else:
                # Regular log line, forward it to the active step.
                s = self._getLastAnnotatedStep()
                if s is None and self.preamble_log is not None:
                    self.preamble_log.addStdout(line)
                else:
                    s.scheduleStdout(line)

        except Exception:
            logging.err(failure.Failure(), 'error while processing annotgated command log:')
