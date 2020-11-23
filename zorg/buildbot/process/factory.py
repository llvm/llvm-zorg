# TODO: Change WithProperties to Interpolate
# TODO: Consider setting codebase to llvm-project.
from collections import OrderedDict

from buildbot.process.factory import BuildFactory
from buildbot.plugins import util, steps

_all_runtimes = frozenset([
    "compiler-rt",
    "libc",
    "libcxx",
    "libcxxabi",
    "libunwind",
    "openmp",
])

class LLVMBuildFactory(BuildFactory):
    """
    TODO: Document

    depends_on_projects is a list of LLVM projects a produced builder
    depends on. If None, it gets discovered depending on other params.

    enable_runtimes is a list of enabled runtimes. If None,
    it gets discovered based on the depends_on_projects list.
    """

    def __init__(self, steps=None, depends_on_projects=None, **kwargs):
        # Cannot use "super" here as BuildFactory is an old style class.
        BuildFactory.__init__(self, steps)

        # Handle the dependencies.
        if depends_on_projects is None:
            # llvm project is always included.
            self.depends_on_projects = set(['llvm'])
        else:
            self.depends_on_projects = frozenset(depends_on_projects)

        enable_runtimes = kwargs.pop('enable_runtimes', None)
        # If specified, we either got a givem list of
        # enabled runtimes, or "auto", or "all".

        if enable_runtimes is None:
            # For the backward compatibility, we do not use
            # enable_runtimes unless it is requested explicitly.
            self.enable_runtimes = frozenset([])
        elif enable_runtimes == "auto":
            # Let's build the list of runtimes based on the given
            # depends_on_projects list.
            self.enable_runtimes = \
                self.depends_on_projects.intersection(_all_runtimes)
        else:
            if  enable_runtimes == "all":
                # Let's replace the "all" placeholder by
                # the actual list of all runtimes.
                self.enable_runtimes = frozenset(_all_runtimes)
            else:
                # Let's just use the given list, no need to discover.
                self.enable_runtimes = frozenset(enable_runtimes)

            # Update the list of dependencies.
            if depends_on_projects is None:
                self.depends_on_projects.update(self.enable_runtimes)

        # Build the list of projects to enable.
        self.enable_projects = \
            self.depends_on_projects.difference(self.enable_runtimes)

        # Directories.
        self.monorepo_dir = kwargs.pop('llvm_srcdir', None)
        self.src_to_build_dir = kwargs.pop('src_to_build_dir', None)
        self.obj_dir = kwargs.pop('obj_dir', None)
        self.install_dir = kwargs.pop('install_dir', None)

        # Preserve the rest of the given extra attributes if any, so we could
        # expand the factory later.
        for k,v in kwargs.items():
            setattr(self, k, v)

        self.monorepo_dir = self.monorepo_dir or "llvm-project"
        self.src_to_build_dir = self.src_to_build_dir or 'llvm'
        self.llvm_srcdir = \
                "{}/{}".format(self.monorepo_dir, self.src_to_build_dir)
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
        # Documentation: http://docs.buildbot.net/current/manual/configuration/buildsteps.html#git
        self.addStep(steps.Git(
                name='Checkout the source code',
                repourl=self.repourl_prefix + "llvm-project.git",
                progress=True,
                workdir=util.WithProperties(self.monorepo_dir),
                retryFetch=True,
                clobberOnFailure=True,
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
                retryFetch=True,
                clobberOnFailure=True,                
                **kwargs))
