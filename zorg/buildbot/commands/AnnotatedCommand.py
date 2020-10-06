#NOTE: Updated to use with Buildbot 2.8.
# pylint: disable=C0103

#TODO: Handle errors in op defers.
#TODO: Redesign of waiting ops completition on the command complete event.

import re

from twisted.internet import defer
from twisted.python import failure
from twisted.python import log as logging

from buildbot.plugins import util
from buildbot.process import buildstep
from buildbot.status import builder
from buildbot.steps import shell

# 1: Create step object.
# 2: yield step.addStep()
# ...
# N+1: yield step.finishStep()

class VirtBuildStep(buildstep.BuildStep):
    def  __init__(self, parent_step, *args, **kwargs):
        self.parent_step = parent_step
        buildstep.BuildStep.__init__(self, *args, **kwargs)

        logging.msg("VirtBuildStep:__init__: %s" % self.name)

        # Step is really unpredictable
        self.useProgress = False

        self.build = self.parent_step.build
        self.master = self.parent_step.build.master
        self.worker = self.parent_step.worker

        self.setText = lambda text: self.realUpdateSummary()
        self.setText2 = lambda text: self.realUpdateSummary()

        self.finished_step = False

        self.stdio_log = None
        self.step_text = ""
        self.step_summary_text = []

    @defer.inlineCallbacks
    def addStep(self):
        logging.msg("VirtBuildStep: adding step with name '%s'" % self.name)

        yield buildstep.BuildStep.addStep(self)
        # Put ourselves into a list of processed steps of the build object.
        self.build.executedSteps.append(self)
        # Init result to SUCCESS by default.
        self.results = builder.SUCCESS
        self.setText([self.name])
        self.stdio_log = yield self.addLog('stdio')

        logging.msg("VirtBuildStep: added step '%s': stepid=%s, buildid=%s" % (
                    self.name, self.stepid, self.build.buildid))


    @defer.inlineCallbacks
    def finishStep(self, results):
        if self.finished_step:
            return
        self.finished_step = True
        if results is not None:
            self.results = results
        hidden = False
        logging.msg("VirtBuildStep: finish step '%s': stepid=%s, buildid=%s, results=%s" % (
                    self.name, self.stepid, self.build.buildid, self.results))
        yield self.master.data.updates.finishStep(self.stepid, self.results,
                                                  hidden)
        # finish unfinished logs
        all_finished = yield self.finishUnfinishedLogs()
        logging.msg("VirtBuildStep: finish step '%s': stepid=%s, buildid=%s" % (
                    self.name, self.stepid, self.build.buildid))
        if not all_finished:
            self.results = builder.EXCEPTION

    #NOTE: we should not run this step in regular way.
    def run(self):
        self.results = builder.EXCEPTION
        return self.results

class BuilderStatus:
    # Order in asceding severity.
    BUILD_STATUS_ORDERING = [
        builder.SUCCESS,
        builder.WARNINGS,
        builder.FAILURE,
        builder.EXCEPTION,
    ]

    @classmethod
    def combine(cls, a, b):
        """Combine two status, favoring the more severe."""
        if a not in cls.BUILD_STATUS_ORDERING:
            return b
        if b not in cls.BUILD_STATUS_ORDERING:
            return a
        a_rank = cls.BUILD_STATUS_ORDERING.index(a)
        b_rank = cls.BUILD_STATUS_ORDERING.index(b)
        pick = max(a_rank, b_rank)
        return cls.BUILD_STATUS_ORDERING[pick]


class ProcessLogShellStep(shell.ShellCommand):
    """ Step that can process log files.

    Delegates actual processing to log_processor, which is a subclass of
    process_log.PerformanceLogParser.

    Sample usage:
    # construct class that will have no-arg constructor.
    log_processor_class = chromium_utils.PartiallyInitialize(
        process_log.GraphingPageCyclerLogProcessor,
        report_link='http://host:8010/report.html,
        output_dir='~/www')
    # We are partially constructing Step because the step final
    # initialization is done by BuildBot.
    step = chromium_utils.PartiallyInitialize(
        chromium_step.ProcessLogShellStep,
        log_processor_class)

    """
    def  __init__(self, log_processor_class=None, *args, **kwargs):
        """
        Args:
          log_processor_class: subclass of
            process_log.PerformanceLogProcessor that will be initialized and
            invoked once command was successfully completed.
        """
        self._result_text = []
        self._log_processor = None
        # If log_processor_class is not None, it should be a class.  Create an
        # instance of it.
        if log_processor_class:
            self._log_processor = log_processor_class()
        shell.ShellCommand.__init__(self, *args, **kwargs)

    def start(self):
        """Overridden shell.ShellCommand.start method.

        Adds a link for the activity that points to report ULR.
        """

        # got_revision could be poisoned by checking out the script itself.
        # So, let's assume that we will get the exactly the same revision
        # this build has been triggered for, and let the script report
        # the revision it checked out.
        self.setProperty('got_revision', self.getProperty('revision'), 'Source')

        self._CreateReportLinkIfNeccessary()
        shell.ShellCommand.start(self)

    def _GetRevision(self):
        """Returns the revision number for the build.

        Result is the revision number of the latest change that went in
        while doing gclient sync. Tries 'got_revision' (from log parsing)
        then tries 'revision' (usually from forced build). If neither are
        found, will return -1 instead.
        """
        revision = None
        try:
            revision = self.build.getProperty('got_revision')
        except KeyError:
            pass  # 'got_revision' doesn't exist (yet)
        if not revision:
            try:
                revision = self.build.getProperty('revision')
            except KeyError:
                pass  # neither exist
        if not revision:
            revision = -1
        return revision

    def commandComplete(self, cmd):
        """Callback implementation that will use log process to parse 'stdio' data.
        """
        if self._log_processor:
            self._result_text = self._log_processor.Process(
                self._GetRevision(), self.getLog('stdio').getText())

    def getText(self, cmd, results):
        text_list = self.describe(True)
        if self._result_text:
            self._result_text.insert(0, '<div class="BuildResultInfo">')
            self._result_text.append('</div>')
            text_list = text_list + self._result_text
        return text_list

    def evaluateCommand(self, cmd):
        shell_result = shell.ShellCommand.evaluateCommand(self, cmd)
        log_result = None
        if self._log_processor and 'evaluateCommand' in dir(self._log_processor):
            log_result = self._log_processor.evaluateCommand(cmd)
        return BuilderStatus.combine(shell_result, log_result)

    def _CreateReportLinkIfNeccessary(self):
        if self._log_processor and self._log_processor.ReportLink():
            self.addURL('results', "%s" % self._log_processor.ReportLink())


class AnnotationObserver_(buildstep.LogLineObserver):
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

    def __init__(self, command=None, *args, **kwargs):
        buildstep.LogLineObserver.__init__(self, *args, **kwargs)
        self.command = command
        self.annotate_status = builder.SUCCESS
        self.halt_on_failure = False
        self.honor_zero_return_code = False

        # A sequence of synchronius operations.
        self._delayed_op_queue = []
        self._proc_op_in_queue = None
        # Current active virtual step, generated by annotation.
        # We cannot process more than one step at the time, so
        # having a single object for that should be enough.
        self._active_vstep = None

        self._dlock = defer.DeferredLock()

        self._re_set = [
            # Support: @@@STEP_LINK@<name>@<url>@@@ (emit link)
            # Also support depreceated @@@link@<name>@<url>@@@
            {
                're'    : AnnotationObserver_._re_step_link,
                'op'    : lambda args: (
                    logging.msg("+++ op: STEP_LINK"),
                    self.queue_op(op=lambda: self.op_addStepLink(args['link_label'],
                                                                 args['link_url']),
                                  name="op_addStepLink")
                )
            },
            # Support: @@@STEP_WARNINGS@@@ (warn on a stage)
            # Also support deprecated @@@BUILD_WARNINGS@@@
             {
                're'    : AnnotationObserver_._re_step_warnings,
                'op'    : lambda args: (
                    logging.msg("+++ op: STEP_WARNINGS"),
                    self.queue_op(op=lambda: self.op_updateStepStatus(builder.WARNINGS),
                                  name="op_updateStepStatus")
                )
            },
            # Support: @@@STEP_FAILURE@@@ (fail a stage)
            # Also support deprecated @@@BUILD_FAILED@@@
            {
                're'    : AnnotationObserver_._re_step_failure,
                'op'    : lambda args: (
                    logging.msg("+++ op: STEP_FAILURE"),
                    self.queue_op(op=lambda: self.op_updateStepStatus(builder.FAILURE),
                                  name="op_updateStepStatus")
                )
            },
            # Support: @@@STEP_EXCEPTION@@@ (exception on a stage)
            # Also support deprecated @@@BUILD_FAILED@@@
            {
                're'    : AnnotationObserver_._re_step_exception,
                'op'    : lambda args: (
                    logging.msg("+++ op: STEP_EXCEPTION"),
                    self.queue_op(op=lambda: self.op_updateStepStatus(builder.EXCEPTION),
                                  name="op_updateStepStatus")
                )
            },
            # Support: @@@HALT_ON_FAILURE@@@ (halt if a step fails immediately)
            {
                're'    : AnnotationObserver_._re_halt_on_failure,
                'op'    : lambda args: (
                    logging.msg("+++ op: HALT_ON_FAILURE"),
                    self.setHaltOnFailure(True)
                )
            },
            # Support: @@@HONOR_ZERO_RETURN_CODE@@@ (succeed on 0 return, even if some
            #     steps have failed)
            {
                're'    : AnnotationObserver_._re_honor_zero_rc,
                'op'    : lambda args: (
                    logging.msg("+++ op: HONOR_ZERO_RC"),
                    self.setHonorZeroReturnCode(True)
                )
            },
            # Support: @@@STEP_CLEAR@@@ (reset step description)
            {
                're'    : AnnotationObserver_._re_step_clear,
                'op'    : lambda args: (
                    logging.msg("+++ op: STEP_CLEAR"),
                    self.queue_op(op=lambda: self.op_updateStepText(text=None),
                                  name="op_updateStepText")
                )
            },
            # Support: @@@STEP_SUMMARY_CLEAR@@@ (reset step summary)
            {
                're'    : AnnotationObserver_._re_step_summary_clear,
                'op'    : lambda args: (
                    logging.msg("+++ op: STEP_SUMMARY_CLEAR"),
                    self.queue_op(op=lambda: self.op_updateStepSummaryInfo(text=None),
                                  name="op_updateStepSummaryInfo")
                )
            },
            # Support: @@@STEP_TEXT@<msg>@@@
            {
                're'    : AnnotationObserver_._re_step_text,
                'op'    : lambda args: (
                    logging.msg("+++ op: STEP_TEXT"),
                    self.queue_op(op=lambda: self.op_updateStepText(text=args['text']),
                                  name="op_updateStepText")
                )
            },
            # Support: @@@STEP_SUMMARY_TEXT@<msg>@@@
            {
                're'    : AnnotationObserver_._re_step_summary_step,
                'op'    : lambda args: (
                    logging.msg("+++ op: STEP_SUMMARY_TEXT"),
                    self.queue_op(op=lambda: self.op_updateStepSummaryInfo(text=args['text']),
                                  name="op_updateStepSummaryInfo")
                )
            },
            # Support: @@@BUILD_STEP <step_name>@@@ (start a new section)
            {
                're'    : AnnotationObserver_._re_build_step,
                'op'    : lambda args: (
                    logging.msg("+++ op: BUILD_STEP"),
                    self.queue_op(op=lambda: self.op_fixupActiveStep(),
                                  name="op_fixupActiveStep"),
                    self.queue_op(op=lambda: self.op_startNewStep(name=args['name'].strip(),
                                                                  logline=args['logline']),
                                  name="op_startNewStep")
                )
            },
        ]

    def queue_op(self, op, name="unspecified"):
        # pylint: disable=unused-argument
        #logging.msg(">>> queue_op: buildid={0}, opname='{1}', op={2}".format(
        #            self.command.build.buildid, name, op))

        if op is not None:
            self._delayed_op_queue.append(op)
        if self._proc_op_in_queue is None and len(self._delayed_op_queue) > 0:
            #self._queue_catchup_all()
            self._queue_catchup_locked()

    @defer.inlineCallbacks
    def _queue_catchup_locked(self):
        yield self._dlock.run(self._queue_catchup_all)

    @defer.inlineCallbacks
    def _queue_catchup_all(self):
        #logging.msg(">>> _queue_catchup_all: buildid={0}".format(
        #            self.command.build.buildid))

        while self._delayed_op_queue:
            op = self._delayed_op_queue.pop(0)
            if op is not None:
                try:
                    d = defer.maybeDeferred(op)
                except Exception:
                    d = defer.fail(failure.Failure())

                # Currently processing deferred operation.
                self._proc_op_in_queue = d

                #TODO: Do we really need this callback here?
                def processed(status):
                    return status
                d.addCallback(processed)
                #TODO: ???:d.addErrback

                yield d

        self._proc_op_in_queue = None

    @defer.inlineCallbacks
    def queue_wait(self):
        logging.msg(">>> queue_wait: buildid={0}".format(
                    self.command.build.buildid))

        yield self._queue_catchup_locked()
        """
        if self._proc_op_in_queue:
            logging.msg(">>> queue_wait: buildid={0}, processing defer".format(
                    self.command.build.buildid))
        if len(self._delayed_op_queue) == 0:
            logging.msg(">>> queue_wait: buildid={0}, empty op queue".format(
                    self.command.build.buildid))
        if self._proc_op_in_queue is None and len(self._delayed_op_queue) > 0:
            yield self._queue_catchup_all()
        """
    def queue_clean(self):
        self._delayed_op_queue = []

    # Synchronius Operations.
    #

    # Adding stdout log for the currently active step.
    def op_addStepStdout(self, text):
        step = self._active_vstep

        # Adding to preamble log in case we still didn't get any vsteps.
        if step is None:
            if self.command.preamble_log is not None:
                self.command.preamble_log.addStdout(text)
            return

        if step.stdio_log is not None:
            step.stdio_log.addStdout(text)

    # Updating a status for the currently active step.
    @defer.inlineCallbacks
    def op_updateStepStatus(self, status):
        """Update current step status and annotation status based on a new event."""

        logging.msg(">>> op_updateStepStatus: buildid=%s, status=%s" % (
                    self.command.build.buildid, status))

        self.annotate_status = BuilderStatus.combine(self.annotate_status, status)

        step = self._active_vstep
        if step is None:
            logging.msg("FATAL ERROR: op_updateStepStatus: no active vstep.")
            #TODO: return defer.fail(...)?
            return

        step.results = BuilderStatus.combine(step.results, status)

        if self.halt_on_failure and step.results in [builder.FAILURE, builder.EXCEPTION]:
            # We got fatal error, which breaks the build. Clean up all scheduled operations
            # and finalize the build.
            self.queue_clean()
            yield self.op_fixupActiveStep()
            self.command.finished(step.results)

    # Updating a step text. None to clean up.
    def op_updateStepText(self, text = None):
        logging.msg(">>> op_updateStepText: buildid=%s, text='%s'" % (
                    self.command.build.buildid, text))

        step = self._active_vstep
        if step is None:
            logging.msg("FATAL ERROR: op_updateStepText: no active vstep.")
            return

        step.step_text = text if text else ""
        step.setText([step.name] + [step.step_text])

    # Updating a step summary info. None to clean up.
    def op_updateStepSummaryInfo(self, text = None):
        logging.msg(">>> op_updateStepSummaryInfo: buildid=%s, text='%s'" % (
                    self.command.build.buildid, text))

        step = self._active_vstep
        if step is None:
            logging.msg("FATAL ERROR: op_updateStepSummaryInfo: no active vstep.")
            return

        if text is not None:
            step.step_summary_text.append(text)
        else:
            step.step_summary_text = []
        # Reflect step status in text2.
        if step.results == builder.EXCEPTION:
            result = ['exception', step.name]
        elif step.results == builder.FAILURE:
            result = ['failed', step.name]
        else:
            result = []

        step.setText2(result + step.step_summary_text)

    def op_addStepLink(self, link_label, link_url):
        logging.msg(">>> op_addStepLink: buildid=%s, link_label='%s', link_url='%s'" % (
                    self.command.build.buildid, link_label, link_url))

        step = self._active_vstep
        if step is None:
            logging.msg("FATAL ERROR: op_addStepLink: no active vstep.")
            return

        step.addURL(link_label, link_url)

    @defer.inlineCallbacks
    def op_startNewStep(self, name, logline = None):
        logging.msg(">>> op_startNewStep: buildid=%s, name='%s'" % (
                    self.command.build.buildid, name))

        if self._active_vstep is not None:
            logging.msg("FATAL ERROR: op_startNewStep: previous vstep is not finished: "
                        "stepid=%s, buildid=%s, name='%s'" % (
                        self._active_vstep.stepid, self._active_vstep.build.buildid,
                        self._active_vstep.name))
            #TODO: return defer.fail(...)?
            return

        step = VirtBuildStep(parent_step=self.command, name=name)
        yield step.addStep()

        # Doing this last so that @@@BUILD_STEP... occurs in the log of the new
        # step.
        if logline is not None:
            step.stdio_log.addStdout(logline)

        self._active_vstep = step
        logging.msg("<<< op_startNewStep: stepid=%s, buildid=%s, name='%s'" % (
                    step.stepid, step.build.buildid, step.name))

    @defer.inlineCallbacks
    def op_fixupActiveStep(self, status = None):
        logging.msg(">>> op_fixupActiveStep: buildid=%s, status='%s'" % (
                    self.command.build.buildid, status))

        step = self._active_vstep
        if step is None:
            #TODO: return defer.fail(...)?
            return

        self._active_vstep = None
        yield step.finishStep(status)
        logging.msg("<<< op_fixupActiveStep: stepid=%s, buildid=%s, name='%s'" % (
                    step.stepid, step.build.buildid, step.name))

    ##

    def errLineReceived(self, line):
        self.outLineReceived(line)

    def setHaltOnFailure(self, enable = True):
        self.halt_on_failure = enable

    def setHonorZeroReturnCode(self, enable = True):
        self.honor_zero_return_code = enable

    def outLineReceived(self, line):
        """This is called once with each line of the test log."""

        # returns: opname, op, args
        def parse_annotate_cmd(ln):
            for k in self._re_set:
                ro = k['re'].search(ln)
                if ro is not None:
                    # Get the regex named group values.
                    # We can get the empty set, but it is ok.
                    args = ro.groupdict()
                    # No need actually, but just in case.
                    if args is None:
                        args = {}
                    # Store the current log line within the arguments.
                    # We will need to save it in some cases.
                    args['logline'] = ln
                    return k['op'], args
            return None, None

        # Add \n if not there, which seems to be the case for log lines from
        # windows agents, but not others.
        if not line.endswith('\n'):
            line += '\n'

        op, args = parse_annotate_cmd(line)
        if op is not None:
            try:
                op(args)
            except Exception:
                logging.msg("Exception occurs while processing annotated command: "
                            "op=%r, args=%s." % (op, args))
                logging.err()
        else:
            # Add to the current secondary log.
            self.queue_op(op=lambda: self.op_addStepStdout(line), name="op_addStepStdout")

    def handleReturnCode(self, return_code):
        # Treat all non-zero return codes as failure.
        # We could have a special return code for warnings/exceptions, however,
        # this might conflict with some existing use of a return code.
        # Besides, applications can always intercept return codes and emit
        # STEP_* tags.
        if return_code == 0:
            self.queue_op(op=lambda: self.op_fixupActiveStep(),
                          name="handleReturnCode.fixupActiveStep")
            if self.honor_zero_return_code:
                self.annotate_status = builder.SUCCESS
        else:
            self.annotate_status = builder.FAILURE
            self.queue_op(op=lambda: self.op_fixupActiveStep(status=builder.FAILURE),
                          name="handleReturnCode.fixupActiveStep(FAILURE)")


class AnnotatedCommand_(ProcessLogShellStep):
    """Buildbot command that knows how to display annotations."""

    # pylint: disable=too-many-ancestors
    def __init__(self, *args, **kwargs):
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
        old_env = kwargs.get('env')
        if not old_env:
            old_env = {}
        env.update(old_env)
        # Change passed in args (ok as a copy is made internally).
        kwargs['env'] = env

        ProcessLogShellStep.__init__(self, *args, **kwargs)
        self.script_observer = AnnotationObserver_(self)
        self.addLogObserver('stdio', self.script_observer)
        self.preamble_log = None

    @defer.inlineCallbacks
    def start(self):
        # Create a preamble log for primary annotate step.
        self.preamble_log = yield self.addLog('preamble')
        r = ProcessLogShellStep.start(self)
        #TODO:VV:
        yield self.script_observer.queue_wait()
        return r

    def interrupt(self, reason):
        logging.msg(">>> AnnotatedCommand::interrupt: buildid=%s" % self.build.buildid)
        self.script_observer.op_fixupActiveStep(status=builder.EXCEPTION)
        #TODO:VV:self.script_observer.queue_wait()
        return ProcessLogShellStep.interrupt(self, reason)

    def evaluateCommand(self, cmd):
        logging.msg(">>> AnnotatedCommand::evaluateCommand: buildid=%s" % self.build.buildid)
        observer_result = self.script_observer.annotate_status
        # Check if ProcessLogShellStep detected a failure or warning also.
        log_processor_result = ProcessLogShellStep.evaluateCommand(self, cmd)
        return BuilderStatus.combine(observer_result, log_processor_result)

    def commandComplete(self, cmd):
        logging.msg(">>> AnnotatedCommand::commandComplete: buildid=%s" % self.build.buildid)
        self.script_observer.handleReturnCode(cmd.rc)
        #TODO:VV:self.script_observer.queue_wait()
        return ProcessLogShellStep.commandComplete(self, cmd)


####


class AnnotationObserver(buildstep.LogLineObserver):
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

    def __init__(self, command=None, *args, **kwargs):
        buildstep.LogLineObserver.__init__(self, *args, **kwargs)
        self.command = command
        self.annotate_status = builder.SUCCESS
        self.halt_on_failure = False
        self.honor_zero_return_code = False
        self.active_log = None

        self._re_set = [
            # Support: @@@STEP_LINK@<name>@<url>@@@ (emit link)
            # Also support depreceated @@@link@<name>@<url>@@@
            {
                're'    : AnnotationObserver._re_step_link,
                'op'    : lambda args: self.command.addURL(args['link_label'], args['link_url'])
            },
            # Support: @@@STEP_WARNINGS@@@ (warn on a stage)
            # Also support deprecated @@@BUILD_WARNINGS@@@
             {
                're'    : AnnotationObserver._re_step_warnings,
                'op'    : lambda args: self.update_status(builder.WARNINGS)
            },
            # Support: @@@STEP_FAILURE@@@ (fail a stage)
            # Also support deprecated @@@BUILD_FAILED@@@
            {
                're'    : AnnotationObserver._re_step_failure,
                'op'    : lambda args: self.update_status(builder.FAILURE)
            },
            # Support: @@@STEP_EXCEPTION@@@ (exception on a stage)
            # Also support deprecated @@@BUILD_FAILED@@@
            {
                're'    : AnnotationObserver._re_step_exception,
                'op'    : lambda args: self.update_status(builder.EXCEPTION)
            },
            # Support: @@@HALT_ON_FAILURE@@@ (halt if a step fails immediately)
            {
                're'    : AnnotationObserver._re_halt_on_failure,
                'op'    : lambda args: self.set_halt_on_failure(True)
            },
            # Support: @@@HONOR_ZERO_RETURN_CODE@@@ (succeed on 0 return, even if some
            #     steps have failed)
            {
                're'    : AnnotationObserver._re_honor_zero_rc,
                'op'    : lambda args: self.set_honor_zero_return_code(True)
            },
            # Support: @@@STEP_CLEAR@@@ (reset step description)
            {
                're'    : AnnotationObserver._re_step_clear,
                'op'    : lambda args: args
            },
            # Support: @@@STEP_SUMMARY_CLEAR@@@ (reset step summary)
            {
                're'    : AnnotationObserver._re_step_summary_clear,
                'op'    : lambda args: args
            },
            # Support: @@@STEP_TEXT@<msg>@@@
            {
                're'    : AnnotationObserver._re_step_text,
                'op'    : lambda args: args # args['text']
            },
            # Support: @@@STEP_SUMMARY_TEXT@<msg>@@@
            {
                're'    : AnnotationObserver._re_step_summary_step,
                'op'    : lambda args: args # args['text']
            },
            # Support: @@@BUILD_STEP <step_name>@@@ (start a new section)
            {
                're'    : AnnotationObserver._re_build_step,
                'op'    : lambda args: self.start_new_section(args['name'], args['logline'])
            },
        ]

    def errLineReceived(self, line):
        self.outLineReceived(line)

    def outLineReceived(self, line):
        """This is called once with each line of the test log."""

        # returns: opname, op, args
        def parse_annotate_cmd(ln):
            for k in self._re_set:
                ro = k['re'].search(ln)
                if ro is not None:
                    # Get the regex named group values.
                    # We can get the empty set, but it is ok.
                    args = ro.groupdict()
                    # No need actually, but just in case.
                    if args is None:
                        args = {}
                    # Store the current log line within the arguments.
                    # We will need to save it in some cases.
                    args['logline'] = ln
                    return k['op'], args
            return None, None

        # Add \n if not there, which seems to be the case for log lines from
        # windows agents, but not others.
        if not line.endswith('\n'):
            line += '\n'

        op, args = parse_annotate_cmd(line)
        if op is not None:
            try:
                op(args)
            except Exception:
                logging.msg("Exception occurs while processing annotated command: "
                            "op=%r, args=%s." % (op, args))
                logging.err()
        else:
            # Add to the current log.
            if self.active_log is not None:
                self.active_log.addStdout(line)
            elif self.command.preamble_log is not None:
                self.command.preamble_log.addStdout(line)

    def handleReturnCode(self, return_code):
        # Treat all non-zero return codes as failure.
        # We could have a special return code for warnings/exceptions, however,
        # this might conflict with some existing use of a return code.
        # Besides, applications can always intercept return codes and emit
        # STEP_* tags.
        if return_code == 0:
            self.finalize_annotation()
            if self.honor_zero_return_code:
                self.annotate_status = builder.SUCCESS
        else:
            self.annotate_status = builder.FAILURE
            self.finalize_annotation(status=builder.FAILURE)

    def set_halt_on_failure(self, v):
        self.halt_on_failure = v

    def set_honor_zero_return_code(self, v):
        self.honor_zero_return_code = v

    def start_new_section(self, name, line):
        if self.active_log is not None:
            self.active_log.finish()
        self.active_log = self.command.addLog(name.strip())
        self.active_log.addStdout(line)

    # Updating a status for the currently active step.
    def update_status(self, status):
        self.annotate_status = BuilderStatus.combine(self.annotate_status, status)

        if self.halt_on_failure and status in [builder.FAILURE, builder.EXCEPTION]:
            self.finalize_annotation(status)
            self.command.finished(status)

    def finalize_annotation(self, status=None):
        if status is not None:
            self.annotate_status = BuilderStatus.combine(self.annotate_status, status)
        if self.active_log is not None:
            self.active_log.finish()
            self.active_log = None

class AnnotatedCommand(shell.ShellCommand):
    """Buildbot command that knows how to display annotations."""

    # pylint: disable=too-many-ancestors
    def __init__(self, *args, **kwargs):
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
        old_env = kwargs.get('env')
        if not old_env:
            old_env = {}
        env.update(old_env)
        # Change passed in args (ok as a copy is made internally).
        kwargs['env'] = env

        shell.ShellCommand.__init__(self, *args, **kwargs)
        self.script_observer = AnnotationObserver(self)
        self.addLogObserver('stdio', self.script_observer)
        self.preamble_log = None

    def start(self):
        # Create a preamble log for primary annotate step.
        self.preamble_log = self.addLog('preamble')
        shell.ShellCommand.start(self)

    def interrupt(self, reason):
        logging.msg(">>> AnnotatedCommand::interrupt: buildid=%s" % self.build.buildid)
        self.script_observer.finalize_annotation(status=builder.EXCEPTION)
        return shell.ShellCommand.interrupt(self, reason)

    def evaluateCommand(self, cmd):
        logging.msg(">>> AnnotatedCommand::evaluateCommand: buildid=%s" % self.build.buildid)
        observer_result = self.script_observer.annotate_status
        # Check if shell.ShellCommand detected a failure or warning also.
        log_processor_result = shell.ShellCommand.evaluateCommand(self, cmd)
        return BuilderStatus.combine(observer_result, log_processor_result)

    def commandComplete(self, cmd):
        logging.msg(">>> AnnotatedCommand::commandComplete: buildid=%s" % self.build.buildid)
        self.script_observer.handleReturnCode(cmd.rc)
        return shell.ShellCommand.commandComplete(self, cmd)
