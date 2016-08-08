from buildbot.process.factory import BuildFactory
from buildbot.steps.source import SVN

svn_repos = {
  'llvm'              : ("%(llvm_srcdir)s",                         'http://llvm.org/svn/llvm-project/llvm/'),
  'clang'             : ("%(llvm_srcdir)s/tools/clang",             'http://llvm.org/svn/llvm-project/cfe/'),
  'clang-tools-extra' : ("%(llvm_srcdir)s/tools/clang/tools/extra", 'http://llvm.org/svn/llvm-project/clang-tools-extra/'),
  'compiler-rt'       : ("%(llvm_srcdir)s/projects/compiler-rt",    'http://llvm.org/svn/llvm-project/compiler-rt/'),
  'lld'               : ("%(llvm_srcdir)s/tools/lld",               'http://llvm.org/svn/llvm-project/lld/'),
  'lnt'               : ("%(llvm_srcdir)s/test/lnt",                'http://llvm.org/svn/llvm-project/lnt/'),
  'test-suite'        : ("%(llvm_srcdir)s/test/test-suite",         'http://llvm.org/svn/llvm-project/test-suite/'),
  'libcxx'            : ("%(llvm_srcdir)s/llvm/projects/libcxx",    'http://llvm.org/svn/llvm-project/libcxx/'),
  'libcxxabi'         : ("%(llvm_srcdir)s/llvm/projects/libcxxabi", 'http://llvm.org/svn/llvm-project/libcxxabi/'),
  'libunwind'         : ("%(llvm_srcdir)s/llvm/projects/libunwind", 'http://llvm.org/svn/llvm-project/libunwind/'),
  'lldb'              : ("%(llvm_srcdir)s/tools/lldb",              'http://llvm.org/svn/llvm-project/lldb/'),
  'llgo'              : ("%(llvm_srcdir)s/tools/llgo",              'http://llvm.org/svn/llvm-project/llgo/'),
  'polly'             : ("%(llvm_srcdir)s/tools/polly",             'http://llvm.org/svn/llvm-project/polly/'),
  'openmp'            : ("%(llvm_srcdir)s/tools/openmp",            'http://llvm.org/svn/llvm-project/openmp/'),
}

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

        # Preserve all the given extra attributes if any, so we could
        # expand the factory later.
        for k,v in kwargs.items():
            setattr(self, k, v)

        # Default source code directory.
        if kwargs.get('llvm_srcdir', None) is None:
            self.llvm_srcdir = "llvm.src"


    @staticmethod
    def pathRelativeToBuild(path, buildPath):
        if path.startswith('/'):
            # The path is absolute. Don't touch it.
            return path
        else:
            return "../" * (buildPath.count("/") + 1) + path


    # llvm_srcdir - Path to the root of the unified source tree.
    # mode - SVN checkout mode.
    # defaultBranch - the default branch to checkout.
    # and so on, see the list of the SVN params. 
    def addSVNSteps(self, llvm_srcdir=None, **kwargs):
        if llvm_srcdir is None:
            llvm_srcdir = self.llvm_srcdir
        if not kwargs.get('mode', None):
            kwargs['mode'] = 'update'
        if not kwargs.get('defaultBranch', None):
            kwargs['defaultBranch'] = 'trunk'

       # Add a SVM step for each project this builder depends on. 
        for project in self.depends_on_projects:
            workdir, baseURL = svn_repos[project]
            self.addStep(
                SVN(name='svn-%s' % project,
                    workdir=workdir % {'llvm_srcdir' : llvm_srcdir},
                    baseURL=baseURL,
                    **kwargs))

