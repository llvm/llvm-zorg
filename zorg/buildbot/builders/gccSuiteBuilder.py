import os
import buildbot
from zorg.buildbot.util.phasedbuilderutils import getBuildDir, setProperty
from zorg.buildbot.util.artifacts import GetCompilerArtifacts
import zorg.buildbot.builders.ClangBuilder as ClangBuilder

def gccRunSuite(languages):
    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    getBuildDir(f)
    # Download compiler from upstream builder.
    GetCompilerArtifacts(f)
    # Load the ignore set.
    #
    # FIXME: This is lame, it is only loaded at startup.
    ignores = ClangBuilder.getClangTestsIgnoresFromPath(
        os.path.expanduser('~/public/clang-tests'),
        'clang-x86_64-darwin10')
    # Convert languages to GCC style names.
    languages = [{'c' : 'gcc', 'c++' : 'g++', 'obj-c' : 'objc',
                  'obj-c++' : 'obj-c++'}[l]
                 for l in languages]
    # Run gcc test suite.
    ClangBuilder.addClangGCCTests(f, ignores,
                                  install_prefix = '%(builddir)s/host-compiler',
                                  languages = languages)
    return f
