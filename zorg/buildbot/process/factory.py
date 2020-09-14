# TODO: Change WithProperties to Interpolate
# TODO: Consider setting codebase to llvm-project.
from collections import OrderedDict

from buildbot.process.factory import BuildFactory
from buildbot.plugins import util, steps

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

        # Directories.
        self.llvm_srcdir = kwargs.pop('llvm_srcdir', None)
        self.obj_dir = kwargs.pop('obj_dir', None)
        self.install_dir = kwargs.pop('install_dir', None)

        # Preserve the rest of the given extra attributes if any, so we could
        # expand the factory later.
        for k,v in kwargs.items():
            setattr(self, k, v)

        self.monorepo_dir = self.llvm_srcdir or "llvm-project"
        self.llvm_srcdir = \
                "%(monorepo_dir)s/llvm" % {'monorepo_dir' : self.monorepo_dir}
        self.obj_dir = \
                self.obj_dir or "build"

        # Repourl_prefix could be specified per builder. Otherwise we use github.
        self.repourl_prefix = kwargs.pop('repourl_prefix', 'https://github.com/llvm/')


    @staticmethod
    def pathRelativeTo(path, basePath):
        if path.startswith('/'):
            # The path is absolute. Don't touch it.
            return path
        else:
            # Remove "current dir" placeholders if any.
            path_nodes = list(filter(lambda x: x != ".", path.split('/')))
            basePath_nodes = list(filter(lambda x: x != ".", basePath.split('/')))

            # Handle edge cases.
            if len(basePath_nodes) == 0:
                return "/".join(path_nodes)
            if len(path_nodes) == 0:
                return "."

            # Skip a common part of the two paths.
            for i in range(0, min(len(path_nodes), len(basePath_nodes))):
                if path_nodes[i] != basePath_nodes[i]:
                    rel_path = \
                        "../" * (len(basePath_nodes) - i) + \
                        "/".join(path_nodes[i:])
                    break
            else:
                # Everything matches.
                rel_path = '.'

            return rel_path


    def addGetSourcecodeSteps(self, **kwargs):
        # Checkout the monorepo.
        self.addStep(steps.Git(
                name='Checkout the source code',
                repourl=self.repourl_prefix + "llvm-project.git",
                progress=True,
                workdir=util.WithProperties(self.monorepo_dir),
                **kwargs))


    # Checkout a given LLVM project to the given directory.
    # TODO: Handle clean property and self.clean attribute.
    def addGetSourcecodeForProject(self, project, name=None, src_dir=None, **kwargs):
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

        self.addStep(steps.Git(
                name=name,
                repourl=_repourl,
                progress=True,
                workdir=util.WithProperties(src_dir),
                **kwargs))
