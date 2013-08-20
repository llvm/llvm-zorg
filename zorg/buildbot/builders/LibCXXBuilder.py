
import buildbot
import buildbot.process.factory
import buildbot.steps.shell
import buildbot.steps.source as source
import buildbot.steps.source.svn as svn
import buildbot.process.properties as properties

import zorg.buildbot.commands.LitTestCommand
import zorg.buildbot.Artifacts as artifacts
import zorg.buildbot.PhasedBuilderUtils as phased_builder_utils

def getLibCXXBuilder():
    f = buildbot.process.factory.BuildFactory()
    
    # Grab the sources.
    src_url = 'http://llvm.org/svn/llvm-project/libcxx/trunk'
    f = phased_builder_utils.SVNCleanupStep(f, 'sources')
    f.addStep(svn.SVN(name='pull.src', mode='full', repourl=src_url,
                      workdir='sources', method='fresh',
                      alwaysUseLatest=False, retry = (60, 5),
                      description='pull.src'))
    
    # Find the build directory and grab the artifacts for our build.
    f = phased_builder_utils.getBuildDir(f)
    f = artifacts.GetCompilerArtifacts(f)
    host_compiler_dir = properties.WithProperties('%(builddir)s/host-compiler')
    f = artifacts.GetCCFromCompilerArtifacts(f, host_compiler_dir)
    f = artifacts.GetCXXFromCompilerArtifacts(f, host_compiler_dir)
    
    # Build libcxx.
    CC = properties.WithProperties('%(cc_path)s')
    CXX = properties.WithProperties('%(cxx_path)s')
    HEADER_INCLUDE = \
        properties.WithProperties('-I %(builddir)s/sources/include')
    SOURCE_LIB = \
        properties.WithProperties('%(builddir)s/sources/lib/libc++.1.dylib')
    
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='build.libcxx', command=['./buildit'], haltOnFailure=True, 
              workdir='sources/lib', 
              env={ 'CC' : CC, 'CXX' : CXX, 'TRIPLE' : '-apple-'}))

    # Get the 'lit' sources.
    f.addStep(svn.SVN(
            name='pull.lit', mode='incremental', method='fresh',
            repourl='http://llvm.org/svn/llvm-project/llvm/trunk/utils/lit',
            workdir='lit.src', alwaysUseLatest=False))

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
            command=['../lit.venv/bin/python', 'setup.py', 'install'],
            workdir='lit.src', haltOnFailure=True))

    # Run the tests with the system's dylib
    f.addStep(zorg.buildbot.commands.LitTestCommand.LitTestCommand(
            name='test.libcxx.system',
            command=[
                properties.WithProperties('%(builddir)s/lit.venv/bin/lit'),
                '-v',
                properties.WithProperties(
                    '--param=cxx_under_test=%(cxx_path)s'),
                '--param=use_system_lib=true',
                'sources/test'],
            workdir='.'))
    # Run the tests with the newly built dylib
    f.addStep(zorg.buildbot.commands.LitTestCommand.LitTestCommand(
            name='test.libcxx.new',
            command=[
                properties.WithProperties('%(builddir)s/lit.venv/bin/lit'),
                '-v',
                properties.WithProperties(
                    '--param=cxx_under_test=%(cxx_path)s'),
                '--param=use_system_lib=false',
                'sources/test'],
            workdir='.'))

    return f
