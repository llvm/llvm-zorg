
import buildbot
import buildbot.process.factory
import buildbot.steps.shell
import buildbot.steps.source as source
import buildbot.steps.source.svn as svn
import buildbot.process.properties as properties

import zorg.buildbot.commands.LitTestCommand
import zorg.buildbot.Artifacts
import zorg.buildbot.PhasedBuilderUtils

def getLibCXXBuilder():
    f = buildbot.process.factory.BuildFactory()
    
    # Grab the sources.
    src_url = 'http://llvm.org/svn/llvm-project/libcxx/trunk'
    f = zorg.buildbot.PhasedBuilderUtils.SVNCleanupStep(f, 'sources')
    f.addStep(svn.SVN(name='pull.src', mode='full', repourl=src_url,
                      workdir='sources', method='fresh',
                      alwaysUseLatest=False, retry = (60, 5),
                      description='pull.src'))
    
    # Find the build directory and grab the artifacts for our build.
    f = zorg.buildbot.PhasedBuilderUtils.getBuildDir(f)
    f = zorg.buildbot.Artifacts.GetCompilerArtifacts(f)
    
    # Build libcxx.
    CC = properties.WithProperties('%(builddir)s/host-compiler/bin/clang')
    cxx_path = '%(builddir)s/host-compiler/bin/clang++'
    CXX = properties.WithProperties(cxx_path)
    HEADER_INCLUDE = \
        properties.WithProperties('-I %(builddir)s/sources/include')
    SOURCE_LIB = \
        properties.WithProperties('%(builddir)s/sources/lib/libc++.1.dylib')
    
    f.addStep(buildbot.steps.shell.ShellCommand(
              name='build.libcxx', command=['./buildit'], haltOnFailure=True, 
              workdir='sources/lib', 
              env={ 'CC' : CC, 'CXX' : CXX, 'TRIPLE' : '-apple-'}))

    # Install a copy of 'lit' in a virtualenv.
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lit.make', command=[
                '/usr/local/bin/virtualenv', 'lit.venv'],
            workdir='.', haltOnFailure=True))
    f.addStep(buildbot.steps.shell.ShellCommand(
            name='venv.lit.install',
            command=['lit.venv/bin/pip', 'install', 'lit'],
            workdir='.', haltOnFailure=True))

    # Run the tests.
    f.addStep(zorg.buildbot.commands.LitTestCommand.LitTestCommand(
            name='test.libcxx',
            command=[
                properties.WithProperties('%(builddir)s/lit.venv/bin/lit'),
                '-v',
                properties.WithProperties(
                    '--param=cxx_under_test=%s' % (cxx_path,)),
                '--param=use_system_lib=true',
                'sources/test'],
            workdir='.'))

    return f
