from twisted.python import log
from twisted.internet import defer
from buildbot.schedulers.triggerable import Triggerable
from buildbot.process.properties import Properties

class LLDBTriggerable(Triggerable):
    """
    This is the scheduler used for lldb android builders,
    Overwrite trigger function, so the triggered builder will
    get changelist based on new changes since their last build.
    The origianl implementation takes changelist from upstream
    triggerer builder, this will be inaccurate in the case that
    some builds in upstream didn't trigger new builds due to
    failure in their early steps.
    """

    def __init__(self, projects, maxChange=100, **kwargs):
        Triggerable.__init__(self, **kwargs)
        self.projects = projects
        self.lastRevision = None
        self.maxChange = maxChange

    def trigger(self, ssid, set_props=None):
        """Trigger this scheduler with the given sourcestamp ID. Returns a
        deferred that will fire when the buildset is finished."""
        # properties for this buildset are composed of our own properties,
        # potentially overridden by anything from the triggering build
        props = Properties()
        props.updateFromProperties(self.properties)
        if set_props:
            props.updateFromProperties(set_props)

        newRevision = [None]
        def getRevision(ss):
            newRevision[0] = ss['revision']
            return ss['revision']

        def getRecentChanges(newRev):
            if self.lastRevision is None:
                return None
            return self.master.db.changes.getRecentChanges(self.maxChange)

        # check the last x changeset and pick up the ones that are between
        # last revision and current revision and belong to interested projects
        def selectChangeSet(changes):
            changeids = []
            if changes is not None:
                for change in changes:
                    if change['revision'] > newRevision[0] or change['revision'] <= self.lastRevision or change['project'] not in self.projects:
                        continue
                    changeids.append(change['changeid'])
            log.msg("LLDBTriggerable: last revision change from %s to %s" % (self.lastRevision, newRevision[0]))
            self.lastRevision = newRevision[0]
            return changeids

        def addBuildset(changeids):
            if changeids:
                log.msg("LLDBTriggerable: addBuildsetForChanges, changeids: %s" % changeids)
                return self.addBuildsetForChanges(reason=self.reason, changeids=changeids, properties=props)
            elif ssid:
                # if this is the first build after master startup, use the source stamp from triggerer build
                # it's possible to write last revision to a file on master, so after master reconfig we could
                # pick up the correct last revision.
                # It's not implemented here because 1) the cases are rare that first build after master restart
                # is preceded by failing builds on triggerer builder, 2) avoid polluting master with project
                # specific cache files
                log.msg("LLDBTriggerable: addBuildsetForSourceStamp")
                return self.addBuildsetForSourceStamp(reason=self.reason, ssid=ssid, properties=props)
            else:
                return self.addBuildsetForLatest(reason=self.reason, properties=props)

        def setup_waiter((bsid,brids)):
            self._waiters[bsid] = d = defer.Deferred()
            self._updateWaiters()
            return d

        d = self.master.db.sourcestamps.getSourceStamp(ssid)
        d.addCallback(getRevision)
        d.addCallback(getRecentChanges)
        d.addCallback(selectChangeSet)
        d.addCallback(addBuildset)
        d.addCallback(setup_waiter)
        return d

