import os

import buildbot
import buildbot.process.factory
from buildbot.steps.source import SVN
from buildbot.steps.shell import ShellCommand 
from buildbot.steps.shell import WarningCountingShellCommand 
from buildbot.process.properties import WithProperties 
from zorg.buildbot.commands.AnnotatedCommand import AnnotatedCommand


def getSanitizerBuildFactoryII(
           clean=False,
           sanity_check=True,
           sanitizers=['sanitizer','asan','lsan','msan','tsan','ubsan','dfsan'],
           build_type="Release",
           common_cmake_options=None,
           python_executable="/usr/bin/python",
           support_32_bit=True,
           env=None,
           jobs="%(jobs)s",
           timeout=1200
           ):

    llvm_srcdir   = "llvm.src"
    llvm_objdir   = "llvm.obj"
    llvm_objdir64 = "llvm64.obj"

    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb', # Make sure Clang doesn't use color escape sequences.
        'PYTHON_EXECUTABLE' : python_executable
                 }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir=".",
                                               env=merged_env))

    # Clean up the source and build tree, if requested.
    if clean:
        f.addStep(ShellCommand(name="rm-llvm_llvm_srcdir",
                               command=["rm", "-rf", llvm_srcdir],
                               haltOnFailure=True,
                               description=["rm src dir", "llvm"],
                               workdir=".",
                               env=merged_env))

        f.addStep(ShellCommand(name="rm-llvm_objdir",
                               command=["rm", "-rf", llvm_objdir],
                               haltOnFailure=True,
                               description=["rm build dir", "llvm"],
                               workdir=".",
                               env=merged_env))

        f.addStep(ShellCommand(name="rm-llvm_objdir64",
                               command=["rm", "-rf", llvm_objdir64],
                               haltOnFailure=True,
                               description=["rm build64 dir", "llvm"],
                               workdir=".",
                               env=merged_env))

    # Get llvm, clang, ompiler-rt, libcxx, libcxxabi
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


    lint_script = os.path.join("..", llvm_srcdir, "projects", "compiler-rt",
                                    "lib", "sanitizer_common", "scripts",
                                    "check_lint.sh")

    # Run annotated command for sanitizer.
    f.addStep(AnnotatedCommand(name="lint",
                               description="lint",
                               timeout=timeout,
                               haltOnFailure=True,
                               command=lint_script,
                               env=merged_env))

    # Create configuration files with cmake.
    f.addStep(ShellCommand(name="create-build-dir",
                               command=["mkdir", "-p", llvm_objdir],
                               haltOnFailure=True,
                               description=["create build dir"],
                               workdir=".",
                               env=merged_env))

    # TODO: make it better way
    if common_cmake_options:
       cmakeCommand = [
            "cmake",
            "-DCMAKE_BUILD_TYPE=%s" % build_type,
            "%s" % common_cmake_options,
            "../%s" % llvm_srcdir]
    else:
       cmakeCommand = [
            "cmake",
            "-DCMAKE_BUILD_TYPE=%s" % build_type,
            "../%s" % llvm_srcdir]

    # Note: ShellCommand does not pass the params with special symbols right.
    # The " ".join is a workaround for this bug.
    f.addStep(ShellCommand(name="cmake-configure",
                               description=["cmake configure"],
                               haltOnFailure=True,
                               command=WithProperties(" ".join(cmakeCommand)),
                               workdir=llvm_objdir,
                               env=merged_env))

    # Build everything.
    f.addStep(WarningCountingShellCommand(name="compile",
                                          command=['nice', '-n', '10',
                                                   'make', WithProperties("-j%s" % jobs)],
                                          haltOnFailure=True,
                                          description=["compiling"],
                                          descriptionDone=["compile"],
                                          workdir=llvm_objdir,
                                          env=merged_env))

    # Run for each sanitizer ['sanitizer','asan','lsan','msan','tsan','ubsan','dfsan']
    if sanity_check and sanitizers:
        for item in sanitizers:
            f.addStep(WarningCountingShellCommand(name="make-check",
                                          command=['make', 'check-%s' % item,
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["make check-%s" % item,],
                                          descriptionDone=["make check-%s" % item,],
                                          workdir=llvm_objdir,
                                          env=merged_env))

    # build 64-bit llvm using clang

    # Create configuration files with cmake.
    f.addStep(ShellCommand(name="create-llvm_build64-dir",
                               command=["mkdir", "-p", llvm_objdir64],
                               haltOnFailure=True,
                               description=["create llvm_build64 dir"],
                               workdir=".",
                               env=merged_env))

    #TODO: make it better way
    clang_path="/usr/home/buildslave/slave_utility_master/sanitizer_test/%s/bin" % llvm_objdir

    if common_cmake_options:
       cmakeCommand_llvm64 = [
            "cmake",
            "-DCMAKE_BUILD_TYPE=%s" % build_type,
            "%s" % common_cmake_options,
            "-DCMAKE_C_COMPILER=%s/clang" % clang_path,
            "-DCMAKE_CXX_COMPILER=%s/clang++" % clang_path,
            "../%s" % llvm_srcdir]
    else:
       cmakeCommand_llvm64 = [
            "cmake",
            "-DCMAKE_BUILD_TYPE=%s" % build_type,
            "-DCMAKE_C_COMPILER=%s/clang" % clang_path,
            "-DCMAKE_CXX_COMPILER=%s/clang++" % clang_path,
            "../%s" % llvm_srcdir]

    # Note: ShellCommand does not pass the params with special symbols right.
    # The " ".join is a workaround for this bug.
    f.addStep(ShellCommand(name="cmake-configure",
                               description=["cmake configure 64-bit llvm"],
                               haltOnFailure=True,
                               command=WithProperties(" ".join(cmakeCommand_llvm64)),
                               workdir=llvm_objdir64,
                               env=merged_env))

    f.addStep(WarningCountingShellCommand(name="compile",
                                          command=['nice', '-n', '10',
                                                   'make', WithProperties("-j%s" % jobs)],
                                          haltOnFailure=True,
                                          description=["compiling"],
                                          descriptionDone=["compile"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

    # Run asan unit tests
    if 'asan' in sanitizers:
        asan_env = {
            'ASAN_PATH' : "%s/projects/compiler-rt/lib/asan" % llvm_objdir64,
            'ASAN_TESTS_PATH' : '${ASAN_PATH}/tests'
                    }
        merged_env.update(asan_env)

        f.addStep(WarningCountingShellCommand(name="make-check-asan",
                                          command=['make', 'check-asan',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["make check-asan"],
                                          descriptionDone=["make check-asan"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

        # Run the unit test binaries
        f.addStep(WarningCountingShellCommand(name="asan-x86_64-Test",
                                          command=['${ASAN_TESTS_PATH}/Asan-x86_64-Test',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["asan-x86_64-Test"],
                                          descriptionDone=["asan-x86_64-Test"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

        f.addStep(WarningCountingShellCommand(name="Asan-x86_64-Noinst-Test",
                                          command=['${ASAN_TESTS_PATH}/Asan-x86_64-Noinst-Test',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["Asan-x86_64-Noinst-Test"],
                                          descriptionDone=["Asan-x86_64-Noinst-Test"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

        if support_32_bit:
            f.addStep(WarningCountingShellCommand(name="Asan-i386-Test",
                                              command=['${ASAN_TESTS_PATH}/Asan-i386-Test',
                                                   WithProperties("-j%s" % jobs)],
                                              haltOnFailure=False,
                                              description=["Asan-i386-Test"],
                                              descriptionDone=["Asan-i386-Test"],
                                              workdir=llvm_objdir64,
                                              env=merged_env))

            f.addStep(WarningCountingShellCommand(name="Asan-i386-Noinst-Test",
                                              command=['${ASAN_TESTS_PATH}/Asan-i386-Noinst-Test',
                                                   WithProperties("-j%s" % jobs)],
                                              haltOnFailure=False,
                                              description=["Asan-i386-Noinst-Test"],
                                              descriptionDone=["Asan-i386-Noinst-Test"],
                                              workdir=llvm_objdir64,
                                              env=merged_env))

    # Run sanitizer_common unit tests                                         
    if 'sanitizer' in sanitizers:
        sanitizer_env = {
            'SANITIZER_COMMON_PATH' : "%s/projects/compiler-rt/lib/sanitizer_common" % llvm_objdir64,
            'SANITIZER_COMMON_TESTS' : '${SANITIZER_COMMON_PATH}/tests'
                    }
        merged_env.update(sanitizer_env)

        f.addStep(WarningCountingShellCommand(name="make-check-sanitizer",
                                          command=['make', 'check-sanitizer',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["make check-sanitizer"],
                                          descriptionDone=["make check-sanitizer"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

        # Run the unit test binaries
        f.addStep(WarningCountingShellCommand(name="Sanitizer-x86_64-Test",
                                          command=['${SANITIZER_COMMON_TESTS}/Sanitizer-x86_64-Test',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["Sanitizer-x86_64-Test"],
                                          descriptionDone=["Sanitizer-x86_64-Test"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

        if support_32_bit:
            f.addStep(WarningCountingShellCommand(name="Sanitizer-i386-Test",
                                              command=['${SANITIZER_COMMON_TESTS}/Sanitizer-i386-Test',
                                                   WithProperties("-j%s" % jobs)],
                                              haltOnFailure=False,
                                              description=["Sanitizer-i386-Test"],
                                              descriptionDone=["Sanitizer-i386-Test"],
                                              workdir=llvm_objdir64,
                                              env=merged_env))

    # Run msan unit tests
    if 'msan' in sanitizers:
        msan_env = {
            'MSAN_PATH' : "%s/projects/compiler-rt/lib/msan" % llvm_objdir64,
                    }
        merged_env.update(msan_env)

        f.addStep(WarningCountingShellCommand(name="make-check-msan",
                                          command=['make', 'check-msan',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["make check-msan"],
                                          descriptionDone=["make check-msan"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

        # Run the unit test binaries
        f.addStep(WarningCountingShellCommand(name="Msan-x86_64-Test",
                                          command=['${MSAN_PATH}/tests/Msan-x86_64-Test',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["Msan-x86_64-Test"],
                                          descriptionDone=["Msan-x86_64-Test"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

    # Run 64-bit tsan unit tests
    if 'tsan' in sanitizers:
        tsan_env = {
            'TSAN_PATH' : 'projects/compiler-rt/lib/tsan'
                    }
        merged_env.update(tsan_env)

        f.addStep(WarningCountingShellCommand(name="make-check-tsan",
                                          command=['make', 'check-tsan',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["make check-tsan"],
                                          descriptionDone=["make check-tsan"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

        # Run the unit test binaries
        f.addStep(WarningCountingShellCommand(name="TsanRtlTest",
                                          command=['$TSAN_PATH/tests/rtl/TsanRtlTest',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["TsanRtlTest"],
                                          descriptionDone=["TsanRtlTest"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

        f.addStep(WarningCountingShellCommand(name="TsanUnitTest",
                                          command=['$TSAN_PATH/tests/unit/TsanUnitTest',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["TsanUnitTest"],
                                          descriptionDone=["TsanUnitTest"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

    # Run 64-bit lsan unit tests
    if 'lsan' in sanitizers:
        lsan_env = {
            'LSAN_PATH' : 'projects/compiler-rt/lib/lsan'
                    }
        merged_env.update(lsan_env)

        f.addStep(WarningCountingShellCommand(name="make-check-lsan",
                                          command=['make', 'check-lsan',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["make check-lsan"],
                                          descriptionDone=["make check-lsan"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

        # Run the unit test binaries
        f.addStep(WarningCountingShellCommand(name="Lsan-x86_64-Test",
                                          command=['$LSAN_PATH/tests/Lsan-x86_64-Test',
                                                   WithProperties("-j%s" % jobs)],
                                          haltOnFailure=False,
                                          description=["Lsan-x86_64-Test"],
                                          descriptionDone=["Lsan-x86_64-Test"],
                                          workdir=llvm_objdir64,
                                          env=merged_env))

    return f
