import re

from twisted.internet import defer

from buildbot.util import unicode2bytes

from buildbot.www.authz.endpointmatchers import Match
from buildbot.www.authz.endpointmatchers import EndpointMatcherBase
from buildbot.www.authz.roles import RolesFromBase
from buildbot.www.authz.authz import Forbidden
from buildbot.www.authz.authz import Authz


class WorkerOwnerMatch(Match):

    def __init__(self, master, workers, **kwargs):
        super().__init__(master, **kwargs)
        self.workerOwners = []
        for worker in workers:
            if 'workerinfo' in worker:
                workerinfo = worker['workerinfo']
                if 'admin' in workerinfo:
                    email = re.search('.*<(.*)>.*', workerinfo['admin'])
                    if email:
                        self.workerOwners.append(email.group(1))

    def getWorkerOwners(self):
        return self.workerOwners


class WorkerEndpointMatcher(EndpointMatcherBase):

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @defer.inlineCallbacks
    def match_WorkerEndpoint(self, epobject, epdict, options):
        worker = yield epobject.get({}, epdict)
        return WorkerOwnerMatch(self.master, [worker])

    @defer.inlineCallbacks
    def match_BuildRequestEndpoint_cancel(self, epobject, epdict, options):
        buildrequest = yield epobject.get({}, epdict)
        if 'builderid' in buildrequest:
            workers = yield self.master.db.workers.getWorkers(builderid=buildrequest['builderid'])
            if workers:
                return WorkerOwnerMatch(self.master, workers)
        return None


class RolesFromWorkerOwner(RolesFromBase):

    def __init__(self, role):
        super().__init__()
        self.role = role

    def getRolesFromUser(self, userDetails, workerOwners):
        if 'email' in userDetails:
            if workerOwners and userDetails['email'] in workerOwners:
                return [self.role]
        return []


class WorkerOwnerAuthz(Authz):

    def __init__(self, roleMatchers=None, **kwargs):
        super().__init__(roleMatchers=roleMatchers, **kwargs)
        self.workerOwnerRoleMatchers = [
            r for r in roleMatchers if isinstance(r, RolesFromWorkerOwner)]
        self.roleMatchers = [  # Remove workerOwnerRoleMatchers from roleMatchers
            r for r in self.roleMatchers if r not in self.workerOwnerRoleMatchers]

    def setMaster(self, master):
        super().setMaster(master)
        for r in self.workerOwnerRoleMatchers:
            r.setAuthz(self)

    @defer.inlineCallbacks
    def assertUserAllowed(self, ep, action, options, userDetails):
        IsWorkerOwnerMatch = False
        roles = self.getRolesFromUser(userDetails)
        for rule in self.allowRules:
            match = yield rule.match(ep, action, options)
            if match is not None:
                # only try to get owner if there are owner Matchers
                if self.ownerRoleMatchers:
                    owner = yield match.getOwner()
                    if owner:
                        for r in self.ownerRoleMatchers:
                            roles.update(set(r.getRolesFromUser(userDetails, owner)))

                if self.workerOwnerRoleMatchers and isinstance(match, WorkerOwnerMatch):
                    IsWorkerOwnerMatch = True
                    workerOwners = match.getWorkerOwners()
                    if workerOwners:
                        for r in self.workerOwnerRoleMatchers:
                            roles.update(set(r.getRolesFromUser(userDetails, workerOwners)))

                for role in roles:
                    if self.match(role, rule.role): # fnmatch or re.match
                        return None

                if not rule.defaultDeny:
                    continue   # check next suitable rule if not denied

                # f" You need to have role '{rule.role}'."
                error_msg = unicode2bytes(" You must be the worker owner." if IsWorkerOwnerMatch else
                                          " You must be an author of the commit triggered the build.")
                raise Forbidden(error_msg)
        return None
