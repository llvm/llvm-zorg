from buildbot.process.factory import BuildFactory
from buildbot.process.properties import WithProperties 
from buildbot.steps.source import SVN
from buildbot.steps.shell import ShellCommand, SetProperty
from buildbot.steps.shell import WarningCountingShellCommand 
from buildbot.steps.slave import RemoveDirectory
from zorg.buildbot.commands.AnnotatedCommand import AnnotatedCommand
from zorg.buildbot.commands.NinjaCommand import NinjaCommand
from zorg.buildbot.conditions.FileConditions import FileDoesNotExist

def getSanitizerBuildFactoryII(
           clean=False,
           sanity_check=True,
           sanitizers=['sanitizer','asan','lsan','msan','tsan','ubsan','dfsan'],
           common_cmake_options=None, # FIXME: For backward compatibility. Will be removed.
           extra_configure_args=[],
           prefixCommand=["nice", "-n", "10"], # For backward compatibility.
           env=None,
           jobs="%(jobs)s",
           timeout=1200):

    llvm_srcdir   = "llvm.src"
    llvm_objdir   = "llvm.obj"

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb', # Make sure Clang doesn't use color escape sequences.
                 }
    if env:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    f = BuildFactory()

    # Clean directory, if requested.
    cleanBuildRequested = lambda step: step.build.getProperty("clean") or clean
    f.addStep(RemoveDirectory(name='clean '+llvm_objdir,
                dir=llvm_objdir,
                haltOnFailure=False,
                flunkOnFailure=False,
                doStepIf=cleanBuildRequested
                ))

    # Get llvm, clang, ompiler-rt, libcxx, libcxxabi, libunwind
    f.addStep(SVN(name='svn-llvm',
                  mode='update',
                  description='svn-llvm',
                  descriptionDone='svn-llvm',
                  baseURL='http://llvm.org/svn/llvm-project/llvm/',
                  defaultBranch='trunk',
                  workdir=llvm_srcdir))

    f.addStep(SVN(name='svn-clang',
                  mode='update',
                  description='svn-clang',
                  descriptionDone='svn-clang',
                  baseURL='http://llvm.org/svn/llvm-project/cfe/',
                  defaultBranch='trunk',
                  workdir='%s/tools/clang' % llvm_srcdir))

    f.addStep(SVN(name='svn-compiler-rt',
                  mode='update',
                  description='svn-compiler-rt',
                  descriptionDone='svn--compiler-rt',
                  baseURL='http://llvm.org/svn/llvm-project/compiler-rt/',
                  defaultBranch='trunk',
                  workdir='%s/projects/compiler-rt' % llvm_srcdir))

    f.addStep(SVN(name='svn-libcxx',
                  mode='update',
                  description='svn-libcxx',
                  descriptionDone='svn-libcxx',
                  baseURL='http://llvm.org/svn/llvm-project/libcxx/',
                  defaultBranch='trunk',
                  workdir='%s/projects/libcxx' % llvm_srcdir))

    f.addStep(SVN(name='svn-libcxxabi',
                  mode='update',
                  description='svn-libcxxabi',
                  descriptionDone='svn-libcxxabi',
                  baseURL='http://llvm.org/svn/llvm-project/libcxxabi/',
                  defaultBranch='trunk',
                  workdir='%s/projects/libcxxabi' % llvm_srcdir))

    f.addStep(SVN(name='svn-libunwind',
                  mode='update',
                  description='svn-libunwind',
                  descriptionDone='svn-libunwind',
                  baseURL='http://llvm.org/svn/llvm-project/libunwind/',
                  defaultBranch='trunk',
                  workdir='%s/projects/libunwind' % llvm_srcdir))

    # Run annotated command for sanitizer.
    if sanity_check:
        f.addStep(
            AnnotatedCommand(
                name="lint check",
                description="lint check",
                timeout=timeout,
                haltOnFailure=False, #True,
                warnOnWarnings=True,
                command=["./check_lint.sh"],
                workdir="%s/projects/compiler-rt/lib/sanitizer_common/scripts" % llvm_srcdir,
                env=merged_env))

    # Always build with ninja.
    cmakeCommand = ["cmake", "-G", "Ninja"]

    # Reconsile configure args with the defaults we want.
    if not any(a.startswith('-DCMAKE_BUILD_TYPE=')   for a in extra_configure_args):
       cmakeCommand.append('-DCMAKE_BUILD_TYPE=Release')
    if not any(a.startswith('-DLLVM_ENABLE_WERROR=') for a in extra_configure_args):
       cmakeCommand.append('-DLLVM_ENABLE_WERROR=OFF')
    if not any(a.startswith('-DLLVM_ENABLE_ASSERTIONS=') for a in extra_configure_args):
       cmakeCommand.append('-DLLVM_ENABLE_ASSERTIONS=ON')
    if not any(a.startswith('-DCMAKE_C_COMPILER') for a in extra_configure_args):
       cmakeCommand.append('-DCMAKE_C_COMPILER=clang')
    if not any(a.startswith('-DCMAKE_CXX_COMPILER') for a in extra_configure_args):
       cmakeCommand.append('-DCMAKE_CXX_COMPILER=clang++')
    if not any(a.startswith('-DCMAKE_CXX_FLAGS') for a in extra_configure_args):
       cmakeCommand.append('-DCMAKE_CXX_FLAGS=\"-std=c++11 -stdlib=libc++\"')
    if not any(a.startswith('-DCMAKE_EXE_LINKER_FLAGS') for a in extra_configure_args):
       cmakeCommand.append('-DCMAKE_EXE_LINKER_FLAGS=-lcxxrt')
    if not any(a.startswith('-DLIBCXXABI_USE_LLVM_UNWINDER=') for a in extra_configure_args):
       cmakeCommand.append('-DLIBCXXABI_USE_LLVM_UNWINDER=ON')
    if not any(a.startswith('-DLLVM_LIT_ARGS=') for a in extra_configure_args):
       cmakeCommand.append('-DLLVM_LIT_ARGS=\"-v\"')

    cmakeCommand += extra_configure_args + ["../%s" % llvm_srcdir]

    # Note: ShellCommand does not pass the params with special symbols right.
    # The " ".join is a workaround for this bug.
    f.addStep(ShellCommand(
        name="cmake-configure",
        description=["cmake configure"],
        haltOnFailure=False, #True,
        warnOnWarnings=True,
        command=WithProperties(" ".join(cmakeCommand)),
        env=merged_env,
        workdir=llvm_objdir,
        doStepIf=FileDoesNotExist("./%s/CMakeCache.txt" % llvm_objdir)))

    # Build everything.
    f.addStep(NinjaCommand(name='build',
                           haltOnFailure=False, #True,
                           warnOnWarnings=True,
                           description=['building', 'with', 'ninja'],
                           descriptionDone=['built', 'with', 'ninja'],
                           workdir=llvm_objdir,
                           env=merged_env))

    # Run tests for each of the requested sanitizers.
    if sanitizers:
        for s in sanitizers:
            f.addStep(
                NinjaCommand(name='test %s' % s,
                             targets=['check-%s' % s],
                             haltOnFailure=False, #True,
                             description=['testing', '%s' % s],
                             descriptionDone=['test', '%s' % s],
                             workdir=llvm_objdir,
                             env=merged_env))

    return f
