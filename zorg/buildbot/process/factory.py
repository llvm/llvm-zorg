from collections import OrderedDict

from buildbot.process.factory import BuildFactory
from buildbot.steps.source import SVN, Git
from buildbot.steps.shell import WithProperties

# NOTE: svn_repos is deprecated and will be removed.
svn_repos = OrderedDict([
  ('llvm'             , ("%(llvm_srcdir)s",                         '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/llvm/')),
  ('clang'            , ("%(llvm_srcdir)s/tools/clang",             '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/cfe/')),
  ('clang-tools-extra', ("%(llvm_srcdir)s/tools/clang/tools/extra", '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/clang-tools-extra/')),
  ('compiler-rt'      , ("%(llvm_srcdir)s/projects/compiler-rt",    '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/compiler-rt/')),
  ('libcxx'           , ("%(llvm_srcdir)s/projects/libcxx",         '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/libcxx/')),
  ('libcxxabi'        , ("%(llvm_srcdir)s/projects/libcxxabi",      '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/libcxxabi/')),
  ('libunwind'        , ("%(llvm_srcdir)s/projects/libunwind",      '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/libunwind/')),
  ('lld'              , ("%(llvm_srcdir)s/tools/lld",               '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/lld/')),
  ('lnt'              , ("test/lnt",                                '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/lnt/')),
  ('test-suite'       , ("test/test-suite",                         '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/test-suite/')),
  ('lldb'             , ("%(llvm_srcdir)s/tools/lldb",              '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/lldb/')),
  ('llgo'             , ("%(llvm_srcdir)s/tools/llgo",              '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/llgo/')),
  ('polly'            , ("%(llvm_srcdir)s/tools/polly",             '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/polly/')),
  ('openmp'           , ("%(llvm_srcdir)s/tools/openmp",            '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/openmp/')),
  ('zorg'             , ("zorg",                                    '%(vcs_protocol:-http)s://llvm.org/svn/llvm-project/zorg/')),
  ])

class LLVMBuildFactory(BuildFactory):
    """
    TODO: Document
    """

    def __init__(self, steps=None, depends_on_projects=None, **kwargs):
        # Cannot use "super" here as BuildFactory is an old style class.
        BuildFactory.__init__(self, steps)

        if depends_on_projects is None:
            self.depends_on_projects = frozenset(['llvm'])
        else:
            self.depends_on_projects = frozenset(depends_on_projects)

        # By default LLVMBuildFactory works in the legacy mode.
        self.is_legacy_mode = kwargs.pop('is_legacy_mode', True)

        # Directories.
        self.llvm_srcdir = kwargs.pop('llvm_srcdir', None)
        self.obj_dir = kwargs.pop('llvm_srcdir', None)
        self.install_dir = kwargs.pop('llvm_srcdir', None)

        # Preserve the rest of the given extra attributes if any, so we could
        # expand the factory later.
        for k,v in kwargs.items():
            setattr(self, k, v)

        if self.is_legacy_mode:
            self.llvm_srcdir = self.llvm_srcdir or "llvm"
            self.obj_dir = self.obj_dir or "build"
        else:
            self.monorepo_dir = self.llvm_srcdir or "llvm-project"
            self.llvm_srcdir = \
                "%(monorepo_dir)s/llvm" % {'monorepo_dir' : self.monorepo_dir}
            self.obj_dir = \
                self.obj_dir or \
                "%(monorepo_dir)s/build" % {'monorepo_dir' : self.monorepo_dir}

            # Repourl could be specified per builder. Otherwise we use github.
            self.repourl_prefix = kwargs.pop('repourl', 'https://github.com/llvm/')


        # Default build directory.
        if kwargs.get('obj_dir', None) is None:
            self.obj_dir = "build"


    @staticmethod
    def pathRelativeToBuild(path, buildPath):
        if path.startswith('/'):
            # The path is absolute. Don't touch it.
            return path
        else:
            # Remove "current dir" placeholders if any.
            path_nodes = list(filter(lambda x: x != ".", path.split('/')))
            buildPath_nodes = list(filter(lambda x: x != ".", buildPath.split('/')))

            # Handle edge cases.
            if len(buildPath_nodes) == 0:
                return "/".join(path_nodes)
            if len(path_nodes) == 0:
                return "."

            # Skip a common part of the two paths.
            for i in range(0, min(len(path_nodes), len(buildPath_nodes))):
                if path_nodes[i] != buildPath_nodes[i]:
                    rel_path = \
                        "../" * (len(buildPath_nodes) - i) + \
                        "/".join(path_nodes[i:])
                    break
            else:
                # Everything matches.
                rel_path = '.'

            return rel_path


    # llvm_srcdir - Path to the root of the unified source tree.
    # mode - SVN checkout mode.
    # defaultBranch - the default branch to checkout.
    # and so on, see the list of the SVN params. 
    # NOTE: addSVNSteps is deprecated and will be removed. Please use addGetSourcecodeSteps instead.
    def addSVNSteps(self, llvm_srcdir=None, **kwargs):
        if llvm_srcdir is None:
            llvm_srcdir = self.llvm_srcdir
        if not kwargs.get('mode', None):
            kwargs['mode'] = 'update'
        if not kwargs.get('defaultBranch', None):
            kwargs['defaultBranch'] = 'trunk'

        # Add a SVM step for each project this builder depends on.
        # We want the projects be always checked out in a certain order.
        for project in svn_repos.keys():
            if project in self.depends_on_projects:
                workdir, baseURL = svn_repos[project]
                self.addStep(
                    SVN(name='svn-%s' % project,
                        workdir=workdir % {'llvm_srcdir' : llvm_srcdir},
                        baseURL=WithProperties(baseURL),
                        **kwargs))


    def addGetSourcecodeSteps(self, **kwargs):
        # Remove 'is_legacy_mode' if it leaked in to kwargs.
        kwargs.pop('is_legacy_mode', None)

        # Bail out if we are in the legacy mode and SVN checkout is required.
        if self.is_legacy_mode:
            self.addSVNSteps(**kwargs)
            return

        # Checkout the monorepo.
        self.addStep(
            Git(name='Checkout the source code',
                repourl=self.repourl_prefix + "llvm-project.git",
                progress=True,
                workdir=WithProperties(self.monorepo_dir),
                **kwargs))


    # Checkout a given LLVM project to the given directory.
    # TODO: Handle clean property and self.clean attribute.
    def addGetSourcecodeForProject(self, project, name=None, src_dir=None, **kwargs):
        # Remove 'is_legacy_mode' if it leaked in to kwargs.
        kwargs.pop('is_legacy_mode', None)

        # Bail out if we are in the legacy mode and SVN checkout is required.
        if self.is_legacy_mode:
            workdir, baseURL = svn_repos[project]

            if not name:
                name = 'svn-%s' % project

            # Check out to the given directory if any.
            # Otherwise this is a part of the unified source tree.
            if src_dir is None:
                src_dir = workdir % {'llvm_srcdir' : self.llvm_srcdir}

            self.addStep(
                SVN(name=name,
                    workdir=src_dir,
                    baseURL=WithProperties(baseURL),
                    **kwargs))
        else:
            # project contains a repo name which is not a part of the monorepo.
            #  We do not enforce it here, though.
            _repourl = kwargs.pop('repourl', None)
            if not _repourl:
                _repourl = self.repourl_prefix + "llvm-%s.git" % project

            if not name:
                name = 'Checkout %s' % project

            # Check out to the given directory if any.
            # Otherwise this is a part of the unified source tree.
            if src_dir is None:
                src_dir = 'llvm-%s' % project

            # Ignore workdir if given. We check out to src_dir.
            kwargs.pop('workdir', None)

            self.addStep(
                Git(name=name,
                    repourl=_repourl,
                    progress=True,
                    workdir=WithProperties(src_dir),
                    **kwargs))
