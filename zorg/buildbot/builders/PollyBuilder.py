import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN, Git
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.process.properties import WithProperties

def installRequiredLibs(f, polly_src):

    cloog_installdir = "cloog.install"

    # Get Cloog and isl
    checkout_cloog = polly_src + '/utils/checkout_cloog.sh'
    cloog_srcdir = WithProperties("%s/cloog.src", "builddir")
    f.addStep(ShellCommand(name="get-cloog",
                           command=[checkout_cloog, cloog_srcdir],
                           description="Get CLooG/isl source code",
                           workdir="."))

    confargs = []
    confargs.append(WithProperties("%s/cloog.src/configure", "builddir"))
    confargs.append(WithProperties("--prefix=%s/cloog.install", "builddir"))
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

    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir="."))
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

    # Install Prerequisites
    installRequiredLibs(f, '%s/tools/polly' % llvm_srcdir)

    # Create configuration files with cmake
    f.addStep(ShellCommand(name="create-build-dir",
                               command=["mkdir", "-p", llvm_objdir],
                               haltOnFailure=False,
                               description=["create build dir"],
                               workdir="."))
    cloogpath = WithProperties("-DCMAKE_PREFIX_PATH=%%(builddir)s/%s"
                                % cloog_installdir)
    cmakeCommand = ["cmake", "../%s" %llvm_srcdir, cloogpath,
		    "-DCMAKE_COLOR_MAKEFILE=OFF", "-DPOLLY_TEST_DISABLE_BAR=ON"]
    f.addStep(ShellCommand(name="cmake-configure",
                               command=cmakeCommand,
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
