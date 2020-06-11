# LLVM buildbot needs to watch multiple projects within a single repository.

# Based on the buildbot.changes.gitpoller.GitPoller source code.
# For buildbot v0.8.5

import time
import tempfile
import os
import re
import itertools

from twisted.python import log
from twisted.internet import defer, utils

from buildbot.util import deferredLocked
from buildbot.changes import base
from buildbot.util import epoch2datetime

class LLVMPoller(base.PollingChangeSource):
    """
    Poll LLVM repository for changes and submit them to the change master.
    Following Multiple Projects.

    This source will poll a remote LLVM git _monorepo_ for changes and submit
    them to the change master."""

    _repourl = "https://github.com/llvm/llvm-project"
    _branch = "master"
    _categories = {
        # Project:       Category:
        'llvm'         : 'llvm',
        'cfe'          : 'clang',
        'polly'        : 'polly',
        'compiler-rt'  : 'compiler-rt',
        'flang'        : 'flang',
        'libc'         : 'libc',
        'libcxx'       : 'libcxx',
        'libcxxabi'    : 'libcxxabi',
        'libunwind'    : 'libunwind',
        'lld'          : 'lld',
        'lldb'         : 'lldb',
        'mlir'         : 'mlir',
        'llgo'         : 'llgo',
        'openmp'       : 'openmp',
        }

    compare_attrs = ["repourl", "branch", "workdir",
                     "pollInterval", "gitbin", "usetimestamps",
                     "category", "project",
                     "projects"]

    projects = None  # Projects and branches to watch.

    def __init__(self, repourl=_repourl, branch=_branch,
                 workdir=None, pollInterval=10*60,
                 gitbin='git', usetimestamps=True,
                 category=None, project=None,
                 pollinterval=-2, fetch_refspec=None,
                 encoding='utf-8', projects=None):

        self.cleanRe = re.compile(r"Require(?:s?)\s*.*\s*clean build", re.IGNORECASE + re.MULTILINE)
        self.cleanCfg = re.compile(r"(CMakeLists\.txt$|\.cmake$|\.cmake\.in$)")

        # projects is a list of projects to watch or None to watch all.
        if projects:
            if isinstance(projects, str) or isinstance(projects, tuple):
                projects = [projects]
            assert isinstance(projects, list)
            assert len(projects) > 0

            # Each project to watch is a string (project name) or a tuple
            # (project name, branch) like ('llvm', 'branches/release_30').
            # But we want it always to be a tuple, so we convert a project
            # name string to a tuple (project, 'master').
            self.projects = set()
            for project in projects:
                if isinstance(project, str):
                    project = (project, branch)

                assert isinstance(project, tuple)
                self.projects.add(project)

        # for backward compatibility; the parameter used to be spelled with 'i'
        if pollinterval != -2:
            pollInterval = pollinterval
        if project is None: project = ''

        self.repourl = repourl
        self.branch = branch
        self.pollInterval = pollInterval
        self.fetch_refspec = fetch_refspec
        self.encoding = encoding
        self.lastChange = time.time()
        self.lastPoll = time.time()
        self.gitbin = gitbin
        self.workdir = workdir
        self.usetimestamps = usetimestamps
        self.category = category
        self.project = project
        self.changeCount = 0
        self.commitInfo  = {}
        self.initLock = defer.DeferredLock()

        if self.workdir == None:
            self.workdir = tempfile.gettempdir() + '/gitpoller_work'
            log.msg("WARNING: LLVMGitPoller using deprecated temporary workdir " +
                    "'%s'; consider setting workdir=" % self.workdir)

    def startService(self):
        # make our workdir absolute, relative to the master's basedir
        if not os.path.isabs(self.workdir):
            self.workdir = os.path.join(self.master.basedir, self.workdir)
            log.msg("LLVMGitPoller: using workdir '%s'" % self.workdir)

        # initialize the repository we'll use to get changes; note that
        # startService is not an event-driven method, so this method will
        # instead acquire self.initLock immediately when it is called.
        if not os.path.exists(self.workdir + r'/.git'):
            d = self.initRepository()
            d.addErrback(log.err, 'while initializing LLVMGitPoller repository')
        else:
            log.msg("LLVMGitPoller repository already exists")

        # call this *after* initRepository, so that the initLock is locked first
        base.PollingChangeSource.startService(self)

    @deferredLocked('initLock')
    def initRepository(self):
        d = defer.succeed(None)
        def make_dir(_):
            dirpath = os.path.dirname(self.workdir.rstrip(os.sep))
            if not os.path.exists(dirpath):
                log.msg('LLVMGitPoller: creating parent directories for workdir')
                os.makedirs(dirpath)
        d.addCallback(make_dir)

        def git_init(_):
            log.msg('LLVMGitPoller: initializing working dir from %s' % self.repourl)
            d = utils.getProcessOutputAndValue(self.gitbin,
                    ['init', self.workdir], env=dict(PATH=os.environ['PATH']))
            d.addCallback(self._convert_nonzero_to_failure)
            d.addErrback(self._stop_on_failure)
            return d
        d.addCallback(git_init)

        def git_remote_add(_):
            d = utils.getProcessOutputAndValue(self.gitbin,
                    ['remote', 'add', 'origin', self.repourl],
                    path=self.workdir, env=dict(PATH=os.environ['PATH']))
            d.addCallback(self._convert_nonzero_to_failure)
            d.addErrback(self._stop_on_failure)
            return d
        d.addCallback(git_remote_add)

        def git_fetch_origin(_):
            args = ['fetch', 'origin']
            self._extend_with_fetch_refspec(args)
            d = utils.getProcessOutputAndValue(self.gitbin, args,
                    path=self.workdir, env=dict(PATH=os.environ['PATH']))
            d.addCallback(self._convert_nonzero_to_failure)
            d.addErrback(self._stop_on_failure)
            return d
        d.addCallback(git_fetch_origin)

        def set_master(_):
            log.msg('LLVMGitPoller: checking out %s' % self.branch)
            if self.branch == 'master': # repo is already on branch 'master', so reset
                d = utils.getProcessOutputAndValue(self.gitbin,
                        ['reset', '--hard', 'origin/%s' % self.branch],
                        path=self.workdir, env=dict(PATH=os.environ['PATH']))
            else:
                d = utils.getProcessOutputAndValue(self.gitbin,
                        ['checkout', '-b', self.branch, 'origin/%s' % self.branch],
                        path=self.workdir, env=dict(PATH=os.environ['PATH']))
            d.addCallback(self._convert_nonzero_to_failure)
            d.addErrback(self._stop_on_failure)
            return d
        d.addCallback(set_master)
        def get_rev(_):
            d = utils.getProcessOutputAndValue(self.gitbin,
                    ['rev-parse', self.branch],
                    path=self.workdir, env={})
            d.addCallback(self._convert_nonzero_to_failure)
            d.addErrback(self._stop_on_failure)
            d.addCallback(lambda (out, err, code) : out.strip())
            return d
        d.addCallback(get_rev)
        def print_rev(rev):
            log.msg("LLVMGitPoller: finished initializing working dir from %s at rev %s"
                    % (self.repourl, rev))
        d.addCallback(print_rev)
        return d

    def describe(self):
        status = ""
        if not self.master:
            status = "[STOPPED - check log]"
        str = 'LLVMGitPoller watching the remote git repository %s, branch: %s %s' \
                % (self.repourl, self.branch, status)
        return str

    @deferredLocked('initLock')
    def poll(self):
        d = self._get_changes()
        d.addCallback(self._process_changes)
        d.addErrback(self._process_changes_failure)
        d.addCallback(self._catch_up)
        d.addErrback(self._catch_up_failure)
        return d

    def _get_commit_comments(self, rev):
        args = ['log', rev, '--no-walk', r'--format=%s%n%b']
        d = utils.getProcessOutput(self.gitbin, args, path=self.workdir, env=dict(PATH=os.environ['PATH']), errortoo=False )
        def process(git_output):
            stripped_output = git_output.strip().decode(self.encoding)
            if len(stripped_output) == 0:
                raise EnvironmentError('could not get commit comment for rev')
            #log.msg("LLVMGitPoller: _get_commit_comments: '%s'" % stripped_output)
            return stripped_output
        d.addCallback(process)
        return d

    def _get_commit_timestamp(self, rev):
        # unix timestamp
        args = ['log', rev, '--no-walk', r'--format=%ct']
        d = utils.getProcessOutput(self.gitbin, args, path=self.workdir, env=dict(PATH=os.environ['PATH']), errortoo=False )
        def process(git_output):
            stripped_output = git_output.strip()
            if self.usetimestamps:
                try:
                    stamp = float(stripped_output)
                    #log.msg("LLVMGitPoller: _get_commit_timestamp: \'%s\'" % stamp)
                except Exception, e:
                        log.msg('LLVMGitPoller: caught exception converting output \'%s\' to timestamp' % stripped_output)
                        raise e
                return stamp
            else:
                return None
        d.addCallback(process)
        return d

    def _get_commit_files(self, rev):
        args = ['log', rev, '--name-only', '--no-walk', r'--format=%n']
        d = utils.getProcessOutput(self.gitbin, args, path=self.workdir, env=dict(PATH=os.environ['PATH']), errortoo=False )
        def process(git_output):
            fileList = git_output.split()
            #log.msg("LLVMGitPoller: _get_commit_files: \'%s\'" % fileList)
            return fileList
        d.addCallback(process)
        return d

    def _get_commit_name(self, rev):
        args = ['log', rev, '--no-walk', r'--format=%aN <%aE>']
        d = utils.getProcessOutput(self.gitbin, args, path=self.workdir, env=dict(PATH=os.environ['PATH']), errortoo=False )
        def process(git_output):
            stripped_output = git_output.strip().decode(self.encoding)
            if len(stripped_output) == 0:
                raise EnvironmentError('could not get commit name for rev')
            #log.msg("LLVMGitPoller: _get_commit_name: \'%s\'" % stripped_output)
            return stripped_output
        d.addCallback(process)
        return d

    def _get_changes(self):
        log.msg('LLVMGitPoller: polling git repo at %s' % self.repourl)

        self.lastPoll = time.time()

        # get a deferred object that performs the fetch
        args = ['fetch', 'origin']
        self._extend_with_fetch_refspec(args)

        # This command always produces data on stderr, but we actually do not care
        # about the stderr or stdout from this command. We set errortoo=True to
        # avoid an errback from the deferred. The callback which will be added to this
        # deferred will not use the response.
        d = utils.getProcessOutput(self.gitbin, args,
                    path=self.workdir,
                    env=dict(PATH=os.environ['PATH']), errortoo=True )

        return d

    def _transform_path(self, fileList):
        """
        Parses the given list of files, and returns a list of two-entry tuples
        (PROJECT, [FILES]) if PROJECT is watched one,
        or None otherwise.

        NOTE: we don't change result path, just extract a project name.
        """
        #log.msg("LLVMGitPoller: _transform_path: got a file list: %s" % fileList)

        if fileList is None or len(fileList) == 0:
            return None

        result = {}

        # turn libcxxabi/include/__cxxabi_config.h into
        #  ("libcxxabi", "libcxxabi/include/__cxxabi_config.h")
        # and filter projects we are not watching.

        for path in fileList:
            pieces = path.split('/')
            project = pieces.pop(0)
            #NOTE:TODO: a dirty hack for backward compatibility.
            if project == "clang":
                project = "cfe"

            #log.msg("LLVMGitPoller: _transform_path: processing path %s: project: %s" % (path, project))
            if self.projects:
                #NOTE: multibranch is not supported.
                #log.msg("LLVMGitPoller: _transform_path: (%s, %s) in projects: %s" % (project, self.branch, (project, self.branch) in self.projects))
                if (project, self.branch) in self.projects:
                    # Collect file path for each detected projects.
                    if project in result:
                        result[project].append(path)
                    else:
                        result[project] = [path]

        #log.msg("LLVMGitPoller: _transform_path: result: %s" % result)
        return [(k, result[k]) for k in result]

    @defer.deferredGenerator
    def _process_changes(self, unused_output):
        # get the change list
        revListArgs = ['log', '%s..origin/%s' % (self.branch, self.branch), r'--format=%H']
        self.changeCount = 0
        d = utils.getProcessOutput(self.gitbin, revListArgs, path=self.workdir,
                                   env=dict(PATH=os.environ['PATH']), errortoo=False )
        wfd = defer.waitForDeferred(d)
        yield wfd
        results = wfd.getResult()

        # process oldest change first
        revList = results.split()
        if not revList:
            return

        revList.reverse()
        self.changeCount = len(revList)

        log.msg('LLVMGitPoller: processing %d changes: %s in "%s"'
                % (self.changeCount, revList, self.workdir) )

        for rev in revList:
            #log.msg('LLVMGitPoller: waiting defer for revision: %s' % rev)
            dl = defer.DeferredList([
                self._get_commit_timestamp(rev),
                self._get_commit_name(rev),
                self._get_commit_files(rev),
                self._get_commit_comments(rev),
            ], consumeErrors=True)

            wfd = defer.waitForDeferred(dl)
            yield wfd
            results = wfd.getResult()
            #log.msg('LLVMGitPoller: got defer results: %s' % results)

            # check for failures
            failures = [ r[1] for r in results if not r[0] ]
            if failures:
                # just fail on the first error; they're probably all related!
                raise failures[0]

            #log.msg('LLVMGitPoller: begin change adding cycle for revision: %s' % rev)

            timestamp, name, files, comments = [ r[1] for r in results ]
            where = self._transform_path(files)
            #log.msg('LLVMGitPoller: walking over transformed path/projects: %s' % where)
            for wh in where:
                where_project, where_project_files = wh
                #log.msg('LLVMGitPoller: processing transformed pair: %s, files:' % where_project, where_project_files)

                properties = dict()
                if self.cleanRe.search(comments) or \
                   any([m for f in where_project_files for m in [self.cleanCfg.search(f)] if m]):
                    log.msg("LLVMGitPoller: creating a change with the 'clean' property for r%s" % rev)
                    properties['clean_obj'] = (True, "change")

                log.msg("LLVMGitPoller: creating a change rev=%s" % rev)
                d = self.master.addChange(
                       author=name,
                       revision=rev,
                       files=where_project_files,
                       comments=comments,
                       when_timestamp=epoch2datetime(timestamp),
                       branch=self.branch,
                       category=self._categories.get(where_project, self.category),
                       project=where_project,
                       # Always promote an external github url of the LLVM project with the changes.
                       repository=self._repourl,
                       src='git',
                       properties=properties)
                wfd = defer.waitForDeferred(d)
                yield wfd
                results = wfd.getResult()

    def _process_changes_failure(self, f):
        log.msg('LLVMGitPoller: repo poll failed')
        log.err(f)
        # eat the failure to continue along the defered chain - we still want to catch up
        return None

    def _catch_up(self, res):
        if self.changeCount == 0:
            log.msg('LLVMGitPoller: no changes, no catch_up')
            return
        log.msg('LLVMGitPoller: catching up tracking branch')
        args = ['reset', '--hard', 'origin/%s' % (self.branch,)]
        d = utils.getProcessOutputAndValue(self.gitbin, args, path=self.workdir, env=dict(PATH=os.environ['PATH']))
        d.addCallback(self._convert_nonzero_to_failure)
        return d

    def _catch_up_failure(self, f):
        log.err(f)
        log.msg('LLVMGitPoller: please resolve issues in local repo: %s' % self.workdir)
        # this used to stop the service, but this is (a) unfriendly to tests and (b)
        # likely to leave the error message lost in a sea of other log messages

    def _convert_nonzero_to_failure(self, res):
        "utility method to handle the result of getProcessOutputAndValue"
        (stdout, stderr, code) = res
        if code != 0:
            raise EnvironmentError('command failed with exit code %d: %s' % (code, stderr))
        return (stdout, stderr, code)

    def _stop_on_failure(self, f):
        "utility method to stop the service when a failure occurs"
        if self.running:
            d = defer.maybeDeferred(lambda : self.stopService())
            d.addErrback(log.err, 'while stopping broken GitPoller service')
        return f

    def _extend_with_fetch_refspec(self, args):
        if self.fetch_refspec:
            if type(self.fetch_refspec) in (list,set):
                args.extend(self.fetch_refspec)
            else:
                args.append(self.fetch_refspec)


# Run: python -m zorg.buildbot.changes.llvmgitpoller
if __name__ == '__main__':
    print "Testing Git LLVMPoller..."
    poller = LLVMPoller(projects = [
            "llvm",
            "cfe",
            "clang-tests-external",
            "clang-tools-extra",
            "polly",
            "compiler-rt",
            "libcxx",
            "libcxxabi",
            "libunwind",
            "lld",
            "lldb",
            "openmp",
            "lnt",
            "test-suite"
        ],
        workdir = os.getcwd()
    )

    # Test _transform_path method.
    fileList = [
        "clang-tools-extra/clang-doc/Generators.cpp",
        "clang-tools-extra/clang-doc/Generators.h",
        "clang-tools-extra/clang-doc/HTMLGenerator.cpp",
        "clang-tools-extra/clang-doc/MDGenerator.cpp",
        "clang-tools-extra/clang-doc/Representation.cpp",
        "clang-tools-extra/clang-doc/Representation.h",
        "clang-tools-extra/clang-doc/YAMLGenerator.cpp",
        "clang-tools-extra/clang-doc/assets/clang-doc-default-stylesheet.css",
        "clang-tools-extra/clang-doc/assets/index.js",
        "clang-tools-extra/clang-doc/stylesheets/clang-doc-default-stylesheet.css",
        "clang-tools-extra/clang-doc/tool/CMakeLists.txt",
        "clang-tools-extra/clang-doc/tool/ClangDocMain.cpp",
        "clang-tools-extra/unittests/clang-doc/CMakeLists.txt",
        "clang-tools-extra/unittests/clang-doc/ClangDocTest.cpp",
        "clang-tools-extra/unittests/clang-doc/ClangDocTest.h",
        "clang-tools-extra/unittests/clang-doc/GeneratorTest.cpp",
        "clang-tools-extra/unittests/clang-doc/HTMLGeneratorTest.cpp",

        "llvm/docs/BugpointRedesign.md",
        "llvm/test/Reduce/Inputs/remove-funcs.sh",
        "llvm/test/Reduce/remove-funcs.ll",
        "llvm/tools/LLVMBuild.txt",
        "llvm/tools/llvm-reduce/CMakeLists.txt",
        "llvm/tools/llvm-reduce/DeltaManager.h",
        "llvm/tools/llvm-reduce/LLVMBuild.txt",
        "llvm/tools/llvm-reduce/TestRunner.cpp",
        "llvm/tools/llvm-reduce/TestRunner.h",
        "llvm/tools/llvm-reduce/deltas/Delta.h",
        "llvm/tools/llvm-reduce/deltas/RemoveFunctions.cpp",
        "llvm/tools/llvm-reduce/deltas/RemoveFunctions.h",
        "llvm/tools/llvm-reduce/llvm-reduce.cpp",

        "openmp/libomptarget/test/mapping/declare_mapper_api.cpp",

        "unknown/lib/unknonw.cpp"
    ]

    where = poller._transform_path(fileList)
    for wh in where:
        where_project, where_project_files = wh
        print "category: %s" % poller._categories.get(where_project, poller.category)
        print "project: %s, files(%s): %s\n" % (where_project, len(where_project_files), where_project_files)
