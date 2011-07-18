import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN, Git
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.process.properties import WithProperties

f = buildbot.process.factory.BuildFactory()

def installRequiredLibs():
    cloog_srcdir = "cloog.src"
    isl_srcdir = "isl.src"
    cloog_installdir = isl_installdir = "cloog.install"

    global f
    # Get Cloog
    f.addStep(Git(repourl='git://repo.or.cz/cloog.git',
                  mode='update',
                  workdir=cloog_srcdir))
    # Get isl
    f.addStep(Git(repourl='git://repo.or.cz/isl.git',
                  mode='update',
                  workdir=isl_srcdir))
    # Build isl
    f.addStep(ShellCommand(name="autogen-isl",
                               command=["./autogen.sh"],
                               haltOnFailure=True,
                               description=["autogen cloog"],
                               workdir=isl_srcdir))
    islconfargs = []
    islconfargs.append(WithProperties("%%(builddir)s/%s/configure"
                                    % isl_srcdir))
    islconfargs.append(WithProperties("--prefix=%%(builddir)s/%s"
                                    % isl_installdir))
    f.addStep(Configure(name="isl-configure",
                        command=islconfargs,
                        workdir=isl_srcdir,
                        description=['isl-configure']))
    f.addStep(ShellCommand(name="build-isl",
                               command=["make"],
                               haltOnFailure=True,
                               description=["build isl"],
                               workdir=isl_srcdir))
    f.addStep(ShellCommand(name="install-isl",
                               command=["make", "install"],
                               haltOnFailure=True,
                               description=["install isl"],
                               workdir=isl_srcdir))
    # Build Cloog
    f.addStep(ShellCommand(name="autogen-cloog",
                               command=["./autogen.sh"],
                               haltOnFailure=True,
                               description=["autogen cloog"],
                               workdir=cloog_srcdir))
    confargs = []
    confargs.append(WithProperties("%%(builddir)s/%s/configure"
                                    % cloog_srcdir))
    confargs.append(WithProperties("--prefix=%%(builddir)s/%s"
                                    % cloog_installdir))
    confargs.append(WithProperties("--with-isl-prefix=%%(builddir)s/%s"
                                    % cloog_installdir))
    confargs.append(WithProperties("--with-isl=system"))
    f.addStep(Configure(name="cloog-configure",
                        command=confargs,
                        workdir=cloog_srcdir,
                        description=['cloog-configure']))
    f.addStep(ShellCommand(name="build-cloog",
                               command=["make"],
                               haltOnFailure=True,
                               description=["build cloog"],
                               workdir=cloog_srcdir))
    f.addStep(ShellCommand(name="install-cloog",
                               command=["make", "install"],
                               haltOnFailure=True,
                               description=["install cloog"],
                               workdir=cloog_srcdir))

def getPollyBuildFactory():
    llvm_srcdir = "llvm.src"
    llvm_objdir = "llvm.obj"
    cloog_installdir = "cloog.install"

    global f
    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir="."))
    # Install Prerequisites
    installRequiredLibs()
    # Get LLVM and Polly
    f.addStep(SVN(name='svn-llvm',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvm_srcdir))
    f.addStep(SVN(name='svn-polly',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/polly/',
                  defaultBranch='trunk',
                  workdir='%s/tools/polly' % llvm_srcdir))
    # Create configuration files with cmake
    f.addStep(ShellCommand(name="create-build-dir",
                               command=["mkdir", llvm_objdir],
                               haltOnFailure=False,
                               description=["create build dir"],
                               workdir="."))
    cloogpath = WithProperties("-DCMAKE_PREFIX_PATH=%%(builddir)s/%s"
                                % cloog_installdir)
    f.addStep(ShellCommand(name="cmake-configure",
                               command=["cmake", "../%s" %llvm_srcdir, cloogpath],
                               haltOnFailure=False,
                               description=["cmake configure"],
                               workdir=llvm_objdir))
    # Build Polly
    f.addStep(ShellCommand(name="build_polly",
                               command=["make"],
                               haltOnFailure=True,
                               description=["build polly"],
                               workdir=llvm_objdir))
    # Test Polly
    f.addStep(ShellCommand(name="test_polly",
                               command=["make", "polly-test"],
                               haltOnFailure=True,
                               description=["test polly"],
                               workdir=llvm_objdir))
    return f
