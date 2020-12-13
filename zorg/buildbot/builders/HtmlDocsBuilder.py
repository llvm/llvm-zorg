from collections import OrderedDict
from importlib import reload

from buildbot.plugins import steps, util
from buildbot.steps.shell import ShellCommand
from buildbot.steps.shell import WarningCountingShellCommand

from zorg.buildbot.process import factory
reload(factory)

llvm_docs = OrderedDict([
  # Project   Build target  Build path    Local path       Remote path
  ("lnt",     ("html",      "docs",       "_build/html/",  "lnt")),
])

# We build with make for now. Change later if needed.
build_cmd = 'make'

def getHtmlDocsBuildFactory(
        depends_on_projects = None,
        clean = False,
        env = None,
        **kwargs):

    if depends_on_projects is None:
        # All the projects by default.
        _depends_on_projects=llvm_docs.keys()
    else:
        # Make a local copy of depends_on_projects, as we are going to modify
        # that.
        _depends_on_projects=depends_on_projects[:]

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Be cautious and disable color output from all tools.
    }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    # HTML Sphinx documentation builds in tree, each in its own directory.
    # For that, make sure the obj_dir is the same as llvm_srcdir.
    src_dir = kwargs.pop('llvm_srcdir', '.')
    f = factory.LLVMBuildFactory(
            clean=clean,
            depends_on_projects=_depends_on_projects,
            llvm_srcdir=src_dir,
            obj_dir=src_dir,
            **kwargs) # Pass through all the extra arguments.

    # Build the documentation
    for project in llvm_docs:

        # Checkout the source code and remove all the untracked files, so
        # we would build a fresh new documentation.
        f.addStep(
            steps.Git(
                name='Checkout the {} source code'.format(project),
                repourl=f.repourl_prefix + "llvm-{}.git".format(project),
                mode='full',
                method='fresh',
                progress=True,
                workdir=util.WithProperties(project),
                env=merged_env,
                **kwargs))

        target, build_path, local_path, remote_path = llvm_docs[project]

        build_dir = util.WithProperties(
                            "{}".format("/".join([
                                project,
                                build_path])))
        f.addStep(
            steps.WarningCountingShellCommand(
                name="Build {} documentation".format(project),
                command=[build_cmd, target],
                haltOnFailure=True,
                workdir=build_dir,
                env=merged_env,
                **kwargs))

        # Publish just built documentation
        f.addStep(
            ShellCommand(
                name="Publish {}".format(project),
                description=[
                    "Publish", "just", "built", "documentation", "for",
                    "{}".format(project)
                    ],
                command=[
                    'rsync',
                    '-vrl',
                    '--delete', '--force', '--delay-updates', '--delete-delay',
                    '--ignore-times',
                    '--checksum',
                    '-p', '--chmod=Du=rwx,Dg=rwx,Do=rx,Fu=rw,Fg=rw,Fo=r',
                    "{}".format(local_path),
                    "lists.llvm.org:web/{}".format(remote_path),
                    ],
                workdir=build_dir,
                env=merged_env,
            )
        )

    return f
