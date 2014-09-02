
import os

import buildbot
import buildbot.process.factory
import buildbot.steps.shell
import buildbot.steps.source as source
import buildbot.steps.source.svn as svn
import buildbot.process.properties as properties

import zorg.buildbot.commands.LitTestCommand as lit_test_command
import zorg.buildbot.util.artifacts as artifacts
import zorg.buildbot.util.phasedbuilderutils as phased_builder_utils

reload(lit_test_command)
reload(artifacts)
reload(phased_builder_utils)

def getLibCXXBuilder(f=None, source_path=None,
                     lit_dir=None):
    if f is None:
        f = buildbot.process.factory.BuildFactory()
        # Find the build directory. We assume if f is passed in that the build
        # directory has already been found.
        f = phased_builder_utils.getBuildDir(f)
    
    # Grab the sources if we are not passed in any.
    if source_path is None:
        source_path = 'sources'
        src_url = 'http://llvm.org/svn/llvm-project/libcxx/trunk'
        f = phased_builder_utils.SVNCleanupStep(f, source_path)
        f.addStep(svn.SVN(name='pull.src', mode='full', repourl=src_url,
                          workdir=source_path, method='fresh',
                          alwaysUseLatest=False, retry = (60, 5),
                          description='pull.src'))
    
    # Grab the artifacts for our build.
    f = artifacts.GetCompilerArtifacts(f)
    host_compiler_dir = properties.WithProperties('%(builddir)s/host-compiler')
    f = artifacts.GetCCFromCompilerArtifacts(f, host_compiler_dir)
    f = artifacts.GetCXXFromCompilerArtifacts(f, host_compiler_dir)
    
    # Build libcxx.
    CC = properties.WithProperties('%(cc_path)s')
    CXX = properties.WithProperties('%(cxx_path)s')
    HEADER_INCLUDE = \
        properties.WithProperties('-I %s' % os.path.join('%(builddir)s',
                                                         source_path,
                                                         'include'))
    SOURCE_LIB = \
        properties.WithProperties(os.path.join('%(builddir)s',
                                               source_path, 'lib',
                                               'libc++.1.dylib'))
    
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='build.libcxx', command=['./buildit'], haltOnFailure=True, 
              workdir=os.path.join(source_path, 'lib'),
              env={ 'CC' : CC, 'CXX' : CXX, 'TRIPLE' : '-apple-'}))

    # Get the 'lit' sources if we need to.
    if lit_dir is None:
        lit_dir = 'lit.src'
        f.addStep(svn.SVN(
            name='pull.lit', mode='incremental', method='fresh',
            repourl='http://llvm.org/svn/llvm-project/llvm/trunk/utils/lit',
            workdir=lit_dir, alwaysUseLatest=False))

    # Install a copy of 'lit' in a virtualenv.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lit.clean',
            command=['rm', '-rf', 'lit.venv'],
            workdir='.', haltOnFailure=True))
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lit.make',
            command=['/usr/local/bin/virtualenv', 'lit.venv'],
            workdir='.', haltOnFailure=True))
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lit.install',
            command=[
                properties.WithProperties('%(builddir)s/lit.venv/bin/python'),
                'setup.py', 'install'],
            workdir=lit_dir, haltOnFailure=True))

    # Run the tests with the system's dylib
    f.addStep(lit_test_command.LitTestCommand(
            name='test.libcxx.system',
            command=[
                properties.WithProperties('%(builddir)s/lit.venv/bin/lit'),
                '-v', '--show-xfail', '--show-unsupported',
                properties.WithProperties(
                    '--param=cxx_under_test=%(cxx_path)s'),
                '--param=use_system_lib=true',
                'sources/test'],
            workdir='.'))
    # Run the tests with the newly built dylib
    f.addStep(lit_test_command.LitTestCommand(
            name='test.libcxx.new',
            command=[
                properties.WithProperties('%(builddir)s/lit.venv/bin/lit'),
                '-v', '--show-xfail', '--show-unsupported',
                properties.WithProperties(
                    '--param=cxx_under_test=%(cxx_path)s'),
                '--param=use_system_lib=false',
                'sources/test'],
            workdir='.'))

    return f
