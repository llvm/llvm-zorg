# LLVM buildbot needs to watch multiple projects within a single repository.
# TODO: Handle both author and committer for a commit to build a correct blame list later.
import re

from twisted.python import log
from datetime import datetime

from twisted.internet import defer
from buildbot.util import bytes2unicode
from buildbot.plugins import changes

class LLVMPoller(changes.GitPoller):
    """
    Poll LLVM repository for changes and submit them for builds scheduling.
    Following Multiple LLVM Projects.

    This source will poll a remote LLVM git _monorepo_ for changes and submit
    them for builds scheduling."""

    _repourl = "https://github.com/llvm/llvm-project"

    compare_attrs = ["repourl", "branches", "workdir",
                     "pollInterval", "gitbin", "usetimestamps",
                     "category", "project",
                     "projects"]

    def _check_branches(branch):
        if branch == "refs/heads/main":
            # Always listen for changes in the main branch.
            return True
        else:
            # We are also interested in the release branches.
            # Some builders will be building changes from there as well.
            return re.search(r"refs\/heads\/release\/\d\d+.*", branch)

    def __init__(self,
                 repourl=_repourl, branches=_check_branches,
                 **kwargs):

        self.cleanRe = re.compile(r"Require(?:s?)\s*.*\s*clean build", re.IGNORECASE + re.MULTILINE)
        self.cleanCfg = re.compile(r"(CMakeLists\.txt$|\.cmake$|\.cmake\.in$)")

        # Note: We always watch all the projects, then schedulers decide
        # to build or not to build.

        super().__init__(repourl=repourl, branches=branches, **kwargs)

    def _transform_path(self, fileList):
        """
        Parses the given list of files, and returns a list of two-entry tuples
        (PROJECT, [FILES]) if PROJECT is watched one,
        or None otherwise.

        NOTE: we don't change result path, just extract a project name.
        """
        #log.msg("LLVMPoller: _transform_path: got a file list: %s" % fileList)

        result = {}

        # It is possible that this commit does not change anything.
        if not fileList:
            return result

        # turn libcxxabi/include/__cxxabi_config.h into
        #  ("libcxxabi", "libcxxabi/include/__cxxabi_config.h")
        # and filter projects we are not watching.

        for path in fileList:
            if not path:
                continue

            pieces = path.split('/')
            project = pieces[0] if len(pieces) > 1 else 'llvm-project'

            #log.msg("LLVMPoller: _transform_path: processing path %s: project: %s" % (path, project))
            # Collect file path for each detected projects.
            if project in result:
                result[project].append(path)
            else:
                result[project] = [path]

        log.msg("LLVMPoller: _transform_path: result: %s" % result)
        return [(k, result[k]) for k in result]

    @defer.inlineCallbacks
    def _process_changes(self, newRev, branch):
        """
        Read changes since last change.

        - Read list of commit hashes.
        - Extract details from each commit.
        - Add changes to database.
        """

        # initial run, don't parse all history
        if not self.lastRev:
            return

        # get the change list
        revListArgs = (['--ignore-missing'] +
                       ['--format=%H', '{}'.format(newRev)] +
                       ['^' + rev
                        for rev in sorted(self.lastRev.values())] +
                       ['--'])
        self.changeCount = 0
        results = yield self._dovccmd('log', revListArgs, path=self.workdir)

        # process oldest change first
        revList = results.split()
        revList.reverse()

        if self.buildPushesWithNoCommits and not revList:
            existingRev = self.lastRev.get(branch)
            if existingRev != newRev:
                revList = [newRev]
                if existingRev is None:
                    # This branch was completely unknown, rebuild
                    log.msg('LLVMPoller: rebuilding {} for new branch "{}"'.format(
                        newRev, branch))
                else:
                    # This branch is known, but it now points to a different
                    # commit than the last time we saw it, rebuild.
                    log.msg('LLVMPoller: rebuilding {} for updated branch "{}"'.format(
                        newRev, branch))

        self.changeCount = len(revList)
        self.lastRev[branch] = newRev

        if self.changeCount:
            log.msg('LLVMPoller: processing {} changes: {} from "{}" branch "{}"'.format(
                    self.changeCount, revList, self.repourl, branch))

        for rev in revList:
            dl = defer.DeferredList([
                self._get_commit_timestamp(rev),
                self._get_commit_author(rev),
                self._get_commit_committer(rev),
                self._get_commit_files(rev),
                self._get_commit_comments(rev),
            ], consumeErrors=True)

            results = yield dl

            # check for failures
            failures = [r[1] for r in results if not r[0]]
            if failures:
                for failure in failures:
                    log.err(
                        failure, "while processing changes for {} {}".format(newRev, branch))
                # just fail on the first error; they're probably all related!
                failures[0].raiseException()

            log.msg('>>> LLVMPoller: begin change adding cycle for revision: %s' % rev)

            timestamp, author, committer, files, comments = [r[1] for r in results]

            where = self._transform_path(files)

            projects = list()
            properties = dict()

            #log.msg('LLVMPoller: walking over transformed path/projects: %s' % where)
            for wh in where:
                where_project, where_project_files = wh
                #log.msg('LLVMPoller: processing transformed pair: %s, files:' % where_project, where_project_files)
                projects += [where_project]

                if self.cleanRe.search(comments) or \
                   any([m for f in where_project_files for m in [self.cleanCfg.search(f)] if m]):
                    log.msg("LLVMPoller: creating a change with the 'clean_obj' property for r%s" % rev)
                    properties['clean_obj'] = (True, "change")

            log.msg("LLVMPoller: creating a change rev=%s" % rev)
            log.msg("  >>> branch=%s, revision=%s, timestamp=%s, author=%s, committer=%s, project=%s, files=%s, comments=\"%s\", properties=%s" % \
                (bytes2unicode(self._removeHeads(branch)),
                bytes2unicode(rev, encoding=self.encoding), datetime.fromtimestamp(timestamp), author, committer,
                projects, files, comments, properties))

            yield self.master.data.updates.addChange(
                       author=author,
                       committer=committer if committer != author else None,
                       revision=bytes2unicode(rev, encoding=self.encoding),
                       files=files,
                       comments=comments,
                       when_timestamp=timestamp,
                       branch=bytes2unicode(self._removeHeads(branch)),
                       category=self.category, ## TODO: Figure out if we could support tags here
                       project=",".join(projects) if projects else "llvm-project",
                       # Always promote an external github url of the LLVM project with the changes.
                       repository=self.repourl if self.repourl.startswith('https://github.com') else self._repourl,
                       src='git', # Must be one of the buildbot.process.users.srcs
                       properties=properties)
