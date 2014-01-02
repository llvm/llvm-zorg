import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN, Git
from buildbot.steps.shell import Configure, ShellCommand
from buildbot.process.properties import WithProperties

from zorg.buildbot.builders import LNTBuilder
from zorg.buildbot.builders import ClangBuilder

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

def checkRequiredLibs(f, polly_src):
    cloog_srcdir = WithProperties("%s/cloog.src", "builddir")
    f.addStep(ShellCommand(name="check-cloog-isl",
                               command=["make", "check"],
                               haltOnFailure=True,
                               description=["check cloog and isl"],
                               workdir=cloog_srcdir))

def getPollyBuildFactory():
    llvm_srcdir = "llvm.src"
    llvm_objdir = "llvm.obj"
    cloog_installdir = "cloog.install"
    polly_srcdir = '%s/tools/polly' % llvm_srcdir
    clang_srcdir = '%s/tools/clang' % llvm_srcdir

    f = buildbot.process.factory.BuildFactory()
    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir="."))
    # Get LLVM, clang and Polly
    f.addStep(SVN(name='svn-llvm',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvm_srcdir))
    f.addStep(SVN(name='svn-clang',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/cfe/',
                  defaultBranch='trunk',
                  workdir=clang_srcdir))
    f.addStep(SVN(name='svn-polly',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/polly/',
                  defaultBranch='trunk',
                  workdir=polly_srcdir))

    # Install Prerequisites
    installRequiredLibs(f, polly_srcdir)

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
    checkRequiredLibs(f, polly_srcdir)
    # Test Polly
    f.addStep(ShellCommand(name="test_polly",
                               command=["make", "polly-test"],
                               haltOnFailure=True,
                               description=["test polly"],
                               workdir=llvm_objdir))
    # Check formatting
    f.addStep(ShellCommand(name="test_polly_format",
                               command=["make", "polly-check-format"],
                               haltOnFailure=False,
                               description=["Check formatting"],
                               workdir=llvm_objdir))
    return f

def AddExternalPollyBuildFactory(f, llvm_installdir):
    cloog_installdir = 'cloog.install'

    polly_srcdir = 'polly.src'
    polly_objdir = 'polly.obj'
    polly_installdir = 'polly.install'
    build_type = 'Release'

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir="."))
    f.addStep(SVN(name='svn-polly',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/polly/',
                  defaultBranch='trunk',
                  workdir=polly_srcdir))

    # Install Prerequisites
    installRequiredLibs(f, polly_srcdir)

    # Create configuration files with cmake
    f.addStep(ShellCommand(name="create-build-dir",
                               command=["mkdir", "-p", polly_objdir],
                               haltOnFailure=False,
                               description=["create build dir"],
                               workdir="."))
    cmakeCommand = ["cmake", "../%s" % polly_srcdir]

    cmakeCommand.append(WithProperties("-DCMAKE_PREFIX_PATH=%%(builddir)s/%s"
                        % cloog_installdir))
    cmakeCommand.append('-DLLVM_INSTALL_ROOT=../' + llvm_installdir)
    cmakeCommand.append('-DCMAKE_BUILD_TYPE=../' + build_type)
    cmakeCommand.append('-DCMAKE_INSTALL_PREFIX=../' + polly_installdir)
    cmakeCommand.append('-DCMAKE_COLOR_MAKEFILE=OFF')

    f.addStep(ShellCommand(name="cmake-configure",
                               command=cmakeCommand,
                               haltOnFailure=False,
                               description=["cmake configure"],
                               workdir=polly_objdir))
    # Build Polly
    f.addStep(ShellCommand(name="build-polly",
                               command=["make"],
                               haltOnFailure=True,
                               description=["build polly"],
                               workdir=polly_objdir))
    f.addStep(ShellCommand(name="remove-polly-install",
                           command=["rm", "-rf", polly_installdir],
                           haltOnFailure=True,
                           description=["remove polly install"],
                           workdir="."))
    f.addStep(ShellCommand(name="install-polly",
                           command=["make", "install"],
                           haltOnFailure=True,
                           description=["install polly"],
                           workdir=polly_objdir))

def getPollyLNTFactory(triple, nt_flags, xfails=[], clean=False, test=False,
                  **kwargs):
    lnt_args = {}
    lnt_arg_names = ['submitURL', 'package_cache', 'testerName', 'reportBuildslave']

    for argname in lnt_arg_names:
        if argname in kwargs:
            lnt_args[argname] = kwargs.pop(argname)

    llvm_install_dir = 'llvm.install.1'

    f = ClangBuilder.getClangBuildFactory(
        triple, outOfDir=True, clean=clean, test=test,
        stage1_config='Release+Asserts', **kwargs)

    f.addStep(ShellCommand(name="install-llvm-and-clang",
                           command=["make", "install"],
                           haltOnFailure=True,
                           description=["install llvm and clang"],
                           workdir="llvm.obj"))

    AddExternalPollyBuildFactory(f, llvm_install_dir)

    nt_flags.append('--cflag=' + '-Xclang')
    nt_flags.append('--cflag=' + '-load')
    nt_flags.append('--cflag=' + '-Xclang')
    nt_flags.append(WithProperties("--cflag=%s/polly.install/lib/LLVMPolly.so",
                                   'builddir'))

    lnt_args['env'] = {'LD_LIBRARY_PATH': WithProperties("%s/cloog.install/lib",
                                   'builddir')}

    # Add an LNT test runner.
    LNTBuilder.AddLNTTestsToFactory(f, nt_flags,
                                    cc_path=(llvm_install_dir+'/bin/clang'),
                                    cxx_path=(llvm_install_dir+'/bin/clang++'),
                                    **lnt_args);

    return f
