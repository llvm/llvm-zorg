import os

import buildbot
import buildbot.process.factory
from buildbot.steps.shell import SetProperty
from buildbot.steps.shell import ShellCommand
from buildbot.steps.slave import RemoveDirectory
from buildbot.steps.source import SVN
from buildbot.process.properties import Property
from zorg.buildbot.builders.Util import getVisualStudioEnvironment
from zorg.buildbot.builders.Util import extractSlaveEnvironment

def getSource(f,llvmTopDir='llvm'):
    f.addStep(SVN(name='svn-llvm',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvmTopDir))
    f.addStep(SVN(name='svn-clang',
                  mode='update', baseURL='http://llvm.org/svn/llvm-project/cfe/',
                  defaultBranch='trunk',
                  workdir='%s/tools/clang' % llvmTopDir))
    f.addStep(SVN(name='svn-compiler-rt',
                  mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/compiler-rt/',
                  defaultBranch='trunk',
                  workdir='%s/tools/compiler-rt' % llvmTopDir))
    return f

def getSanitizerWindowsBuildFactory(
            clean=False,
            cmake='cmake',

            # Default values for VS devenv and build configuration
            vs=r"""%VS120COMNTOOLS%""",
            config='Release',
            target_arch='x86',

            extra_cmake_args=[],
            test=False):

    ############# PREPARING
    f = buildbot.process.factory.BuildFactory()

    # Determine Slave Environment and Set MSVC environment.
    f.addStep(SetProperty(
        command=getVisualStudioEnvironment(vs, target_arch),
        extract_fn=extractSlaveEnvironment))

    f = getSource(f,'llvm')

    # Global configurations
    build_dir='build'

    ############# CLEANING
    cleanBuildRequested = lambda step: step.build.getProperty("clean") or clean
    f.addStep(RemoveDirectory(name='clean '+build_dir,
                dir=build_dir,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=cleanBuildRequested
                ))

    f.addStep(ShellCommand(name='cmakegen',
                           command=[cmake, "-G", "Ninja", "../llvm",
                                    "-DCMAKE_BUILD_TYPE="+config,
                                    "-DLLVM_ENABLE_ASSERTIONS=ON"]
                                   + extra_cmake_args,
                           workdir=build_dir))

    f.addStep(ShellCommand(name='cmake',
                           command=['cmakegen.bat'],
                           haltOnFailure=True,
                           description='cmake gen',
                           workdir=build_dir,

    # Build compiler-rt first to speed up detection of Windows-specific
    # compiler-time errors in the sanitizers runtime.
    f.addStep(NinjaCommand(name='build compiler-rt',
                           targets=['compiler-rt'],
                           haltOnFailure=True,
                           description='ninja compiler-rt',
                           workdir=build_dir,
                           env=Property('slave_env')))

    f.addStep(NinjaCommand(name='build',
                           haltOnFailure=True,
                           description='ninja build',
                           workdir=build_dir,
                           env=Property('slave_env')))

    test_targets = ['check-asan','check-asan-dynamic','check-sanitizer']
    ignoreTestFail = bool(test != 'ignoreFail')
    f.addStep(NinjaCommand(name='run tests',
                           targets=test_cmd,
                           flunkOnFailure=ignoreTestFail,
                           description='ninja test',
                           workdir=build_dir,
                           doStepIf=bool(test),
                           env=Property('slave_env')))
    
    return f
