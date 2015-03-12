# LLVM buildbot needs to watch multiple projects within a single repository.

# Based on the buildbot.changes.svnpoller.SVNPoller source code.

from twisted.python import log
from twisted.internet import defer, utils

from buildbot import util
from buildbot.changes import base

import xml.dom.minidom
import os, urllib, collections

class LLVMPoller(base.PollingChangeSource, util.ComparableMixin):
    """
    Poll LLVM repository for changes and submit them to the change master.
    Following Multiple Projects.
    """

    _svnurl="http://llvm.org/svn/llvm-project"
    _revlinktmpl="http://llvm.org/viewvc/llvm-project/?view=rev&revision=%s"

    compare_attrs = ["svnurl", "split_svn_path",
                     "svnuser", "svnpasswd",
                     "pollInterval", "histmax",
                     "svnbin", "category", "cachepath",
                     "projects"]

    parent = None # filled in when we're added
    last_change = None
    loop = None
    projects = None  # Projects and branches to watch.

    def __init__(self, svnurl=_svnurl, svnuser=None, svnpasswd=None,
                 pollInterval=2*60, histmax=10,
                 svnbin='svn', revlinktmpl=_revlinktmpl, category=None,
                 projects=None, cachepath=None):

        # projects is a list of projects to watch or None to watch all.
        if projects:
            if isinstance(projects, str) or isinstance(projects, tuple):
                projects = [projects]
            assert isinstance(projects, list)
            assert len(projects) > 0

            # Each project to watch is a string (project name) or a tuple
            # (project name, branch) like ('llvm', 'branches/release_30').
            # But we want it always to be a tuple, so we convert a project
            # name string to a tuple (project, 'trunk').
            self.projects = set()
            for project in projects:
                if isinstance(project, str):
                    project = (project, 'trunk')

                assert isinstance(project, tuple)
                self.projects.add(project)

        if svnurl.endswith("/"):
            svnurl = svnurl[:-1] # strip the trailing slash.
        self.svnurl = svnurl
        self._prefix = svnurl  # svnurl is the LLVM repository root.

        self.svnuser = svnuser
        self.svnpasswd = svnpasswd

        self.revlinktmpl = revlinktmpl

        self.environ = os.environ.copy() # include environment variables
                                         # required for ssh-agent auth.

        self.svnbin = svnbin
        self.pollInterval = pollInterval
        self.histmax = histmax
        self.category = category

        self.cachepath = cachepath
        if self.cachepath and os.path.exists(self.cachepath):
            try:
                f = open(self.cachepath, "r")
                self.last_change = int(f.read().strip())
                log.msg("LLVMPoller(%s): Setting last_change to %s" % (self.svnurl, self.last_change))
                f.close()
                # try writing it, too
                f = open(self.cachepath, "w")
                f.write(str(self.last_change))
                f.close()
            except:
                self.cachepath = None
                log.msg(("LLVMPoller(%s): Cache file corrupt or unwriteable; " +
                        "skipping and not using") % self.svnurl)
                log.err()

    def describe(self):
        return "LLVMPoller: watching %s" % self.svnurl

    def poll(self):
        # Return value is only used for unit testing.
        if self.projects:
            log.msg("LLVMPoller(%s): Polling %s projects" % (self.svnurl, self.projects))
        else:
            log.msg("LLVMPoller(%s): Polling all projects" % self.svnurl)

        d = defer.succeed(None)

        d.addCallback(self.get_logs)
        d.addCallback(self.parse_logs)
        d.addCallback(self.get_new_logentries)
        d.addCallback(self.create_changes)
        d.addCallback(self.submit_changes)
        d.addCallback(self.finished_ok)
        d.addErrback(log.err, 'LLVMPoller: Error in  while polling') # eat errors

        return d

    def getProcessOutput(self, args):
        # This exists so we can override it during the unit tests.
        d = utils.getProcessOutput(self.svnbin, args, self.environ)
        return d

    def get_logs(self, _):
        args = []
        args.extend(["log", "--xml", "--verbose", "--non-interactive"])
        if self.svnuser:
            args.extend(["--username=%s" % self.svnuser])
        if self.svnpasswd:
            args.extend(["--password=%s" % self.svnpasswd])
        args.extend(["--limit=%d" % (self.histmax), self.svnurl])
        d = self.getProcessOutput(args)
        return d

    def parse_logs(self, output):
        # Parse the XML output, return a list of <logentry> nodes.
        try:
            doc = xml.dom.minidom.parseString(output)
        except xml.parsers.expat.ExpatError:
            log.msg("LLVMPoller(%s): LLVMPoller.parse_logs: ExpatError in '%s'" % (self.svnurl, output))
            raise
        logentries = doc.getElementsByTagName("logentry")
        return logentries

    def get_new_logentries(self, logentries):
        last_change = old_last_change = self.last_change

        # Given a list of logentries, calculate new_last_change, and
        # new_logentries, where new_logentries contains only the ones after
        # last_change.

        new_last_change = None
        new_logentries = []
        if logentries:
            new_last_change = int(logentries[0].getAttribute("revision"))

            if last_change is None:
                # If this is the first time we've been run, ignore any changes
                # that occurred before now. This prevents a build at every
                # startup.
                log.msg('LLVMPoller(%s): Starting at change %s' % (self.svnurl, new_last_change))
            elif last_change == new_last_change:
                # An unmodified repository will hit this case.
                log.msg('LLVMPoller(%s): No changes' % self.svnurl)
                assert len(new_logentries) == 0
                return [] # No new logentries.
            else:
                for el in logentries:
                    if last_change == int(el.getAttribute("revision")):
                        break
                    new_logentries.append(el)
                new_logentries.reverse() # Return the oldest first.

        self.last_change = new_last_change
        log.msg('LLVMPoller(%s): Last change set from %s to %s' %
                (self.svnurl, old_last_change, new_last_change))
        return new_logentries

    def _get_text(self, element, tag_name):
        try:
            child_nodes = element.getElementsByTagName(tag_name)[0].childNodes
            text = "".join([t.data for t in child_nodes])
        except:
            text = "<unknown>"
        return text

    def _transform_path(self, path):
        """
        Parses the given path, and returns a three-entry tuple
        (PROJECT, BRANCH, FILEPATH) if PROJECT is watched one,
        or None otherwise.
        """

        relative_path = path
        if relative_path.startswith(self._prefix):
            relative_path = path[len(self._prefix):]
        if relative_path.startswith("/"):
            relative_path = relative_path[1:]

        # turn llvm/trunk/lib/CodeGen/Analysis.cpp into
        #  ("llvm", "trunk", "lib/CodeGen/Analysis.cpp")
        # llvm/branches/release_30/lib/CodeGen/Analysis.cpp into
        #  ("llvm", "branches/release_30", "lib/CodeGen/Analysis.cpp")
        # and llvm/tags/RELEASE_30/rc1/lib/CodeGen/Analysis.cpp into
        #  ("llvm", "tags/RELEASE_30/rc1", "lib/CodeGen/Analysis.cpp")
        # and filter projects/branches we are not watching.

        pieces = relative_path.split('/')
        project = pieces.pop(0)
        branch = None
        file_path = None

        if pieces[0] == "trunk":
            branch = pieces[0]
            file_path = '/'.join(pieces[1:])
        elif pieces[0] == "branches":
            branch = '/'.join(pieces[0:2])
            file_path = '/'.join(pieces[2:])
        elif pieces[0] == "tags":
            branch = '/'.join(pieces[0:3])
            file_path = '/'.join(pieces[3:])
        else:
            # Something we do not expect.
            log.msg("LLVMPoller(%s) cannot parse the path (%s). Ignored." % (self.svnurl, path))
            return None

        if self.projects:
            if (project, branch) not in self.projects:
                return None
        return (project, branch, file_path)

    def create_changes(self, new_logentries):
        changes = []

        categories = {
            # Project:       Category:
            'llvm'         : 'llvm',
            'cfe'          : 'clang',
            'polly'        : 'polly',
            'compiler-rt'  : 'compiler-rt',
            'libcxx'       : 'libcxx',
            'libcxxabi'    : 'libcxxabi',
            'lld'          : 'lld',
            'lldb'         : 'lldb',
            'llgo'         : 'llgo',
            'openmp'       : 'openmp',
            }

        for el in new_logentries:
            revision = str(el.getAttribute("revision"))

            revlink = ''

            if self.revlinktmpl:
                if revision:
                    revlink = self.revlinktmpl % urllib.quote_plus(revision)

            log.msg("LLVMPoller(%s): Adding change revision %s" % (self.svnurl, revision))
            author   = self._get_text(el, "author")
            comments = self._get_text(el, "msg")
            # there is a "date" field, but it provides localtime in the
            # repository's timezone, whereas we care about buildmaster's
            # localtime (since this will get used to position the boxes on
            # the Waterfall display, etc). So ignore the date field, and
            # addChange will fill in with the current time
            branches = {}
            try:
                pathlist = el.getElementsByTagName("paths")[0]
            except IndexError: # weird, we got an empty revision
                log.msg("LLVMPoller(%s): Ignoring commit with no paths." % self.svnurl)
                continue

            for p in pathlist.getElementsByTagName("path"):
                action = p.getAttribute("action")
                path = "".join([t.data for t in p.childNodes])
                # the rest of buildbot is certaily not yet ready to handle
                # unicode filenames, because they get put in RemoteCommands
                # which get sent via PB to the buildslave, and PB doesn't
                # handle unicode.
                path = path.encode("ascii")
                if path.startswith("/"):
                    path = path[1:]
                where = self._transform_path(path)

                # if 'where' is None, the file was outside any project that
                # we care about and we should ignore it.
                if where:
                    assert len(where) == 3
                    project, branch, filename = where
                    if not branch in branches:
                        branches[branch] = {'files': []}
                    branches[branch]['files'].append(filename)

                    if not branches[branch].has_key('action'):
                        branches[branch]['action'] = action

            for branch in branches.keys():
                action = branches[branch]['action']
                files  = branches[branch]['files']
                number_of_files_changed = len(files)

                if action == u'D' and number_of_files_changed == 1 and files[0] == '':
                    log.msg("LLVMPoller(%s): Ignoring deletion of branch '%s'" % (self.svnurl, branch))
                else:
                    chdict = dict(author=author,
                                  files=files,
                                  comments=comments,
                                  revision=revision,
                                  branch=branch,
                                  revlink=revlink,
                                  category=categories.get(project, None),
                                  repository=self.svnurl,
                                  project=project)
                    changes.append(chdict)

        return changes

    @defer.deferredGenerator
    def submit_changes(self, changes):
        for chdict in changes:
            wfd = defer.waitForDeferred(self.master.addChange(**chdict))
            yield wfd
            wfd.getResult()

    def finished_ok(self, res):
        if self.cachepath:
            f = open(self.cachepath, "w")
            f.write(str(self.last_change))
            f.close()

        log.msg("LLVMPoller: Finished polling with res %s" % res)
        return res
