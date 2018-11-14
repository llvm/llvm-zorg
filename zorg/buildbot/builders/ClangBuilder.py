import buildbot
import buildbot.process.factory
import copy
import os
from datetime import datetime

from buildbot.process.properties import WithProperties, Property
from buildbot.steps.shell import Configure, ShellCommand, SetProperty
from buildbot.steps.shell import WarningCountingShellCommand
from buildbot.steps.source import SVN
from buildbot.steps.transfer import FileDownload

import zorg.buildbot.util.artifacts as artifacts
import zorg.buildbot.builders.Util as builders_util
import zorg.buildbot.util.phasedbuilderutils as phasedbuilderutils
import zorg.buildbot.commands as commands
import zorg.buildbot.commands.BatchFileDownload as batch_file_download
import zorg.buildbot.commands.LitTestCommand as lit_test_command
from zorg.buildbot.conditions.FileConditions import FileDoesNotExist
from zorg.buildbot.process.factory import LLVMBuildFactory

def getClangBuildFactory(
            triple=None,
            clean=True,
            test=True,
            package_dst=None,
            run_cxx_tests=False,
            examples=False,
            valgrind=False,
            valgrindLeakCheck=False,
            useTwoStage=False,
            completely_clean=False, 
            make='make',
            jobs="%(jobs)s",
            stage1_config='Debug+Asserts',
            stage2_config='Release+Asserts',
            env={}, # Environmental variables for all steps.
            extra_configure_args=[],
            stage2_extra_configure_args=[],
            use_pty_in_tests=False,
            trunk_revision=None,
            force_checkout=False,
            extra_clean_step=None,
            checkout_compiler_rt=False,
            checkout_lld=False,
            run_gdb=False,
            run_modern_gdb=False,
            run_gcc=False):
    # Prepare environmental variables. Set here all env we want everywhere.
    merged_env = {
        'TERM' : 'dumb' # Make sure Clang doesn't use color escape sequences.
                 }
    if env is not None:
        # Overwrite pre-set items with the given ones, so user can set anything.
        merged_env.update(env)

    llvm_srcdir = "llvm.src"
    llvm_1_objdir = "llvm.obj"
    llvm_1_installdir = "llvm.install.1"
    llvm_2_objdir = "llvm.obj.2"
    llvm_2_installdir = "llvm.install"

    f = buildbot.process.factory.BuildFactory()

    # Determine the build directory.
    f.addStep(buildbot.steps.shell.SetProperty(name="get_builddir",
                                               command=["pwd"],
                                               property="builddir",
                                               description="set build dir",
                                               workdir=".",
                                               env=merged_env))

    # Blow away completely, if requested.
    if completely_clean:
        f.addStep(ShellCommand(name="rm-llvm.src",
                               command=["rm", "-rf", llvm_srcdir],
                               haltOnFailure=True,
                               description=["rm src dir", "llvm"],
                               workdir=".",
                               env=merged_env))

    # Checkout sources.
    if trunk_revision:
        # The SVN build step provides no mechanism to check out a specific revision
        # based on a property, so just run the commands directly here.
        svn_co = ['svn', 'checkout']
        if force_checkout:
            svn_co += ['--force']
        svn_co += ['--revision', WithProperties(trunk_revision)]

        svn_co_llvm = svn_co + \
          [WithProperties('http://llvm.org/svn/llvm-project/llvm/trunk@%s' %
                          trunk_revision),
           llvm_srcdir]
        svn_co_clang = svn_co + \
          [WithProperties('http://llvm.org/svn/llvm-project/cfe/trunk@%s' %
                          trunk_revision),
           '%s/tools/clang' % llvm_srcdir]
        svn_co_clang_tools_extra = svn_co + \
          [WithProperties('http://llvm.org/svn/llvm-project/clang-tools-extra/trunk@%s' %
                          trunk_revision),
           '%s/tools/clang/tools/extra' % llvm_srcdir]

        f.addStep(ShellCommand(name='svn-llvm',
                               command=svn_co_llvm,
                               haltOnFailure=True,
                               workdir='.'))
        f.addStep(ShellCommand(name='svn-clang',
                               command=svn_co_clang,
                               haltOnFailure=True,
                               workdir='.'))
        f.addStep(ShellCommand(name='svn-clang-tools-extra',
                               command=svn_co_clang_tools_extra,
                               haltOnFailure=True,
                               workdir='.'))
    else:
        f.addStep(SVN(name='svn-llvm',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/llvm/',
                      defaultBranch='trunk',
                      workdir=llvm_srcdir))
        f.addStep(SVN(name='svn-clang',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/cfe/',
                      defaultBranch='trunk',
                      workdir='%s/tools/clang' % llvm_srcdir))
        f.addStep(SVN(name='svn-clang-tools-extra',
                      mode='update',
                      baseURL='http://llvm.org/svn/llvm-project/clang-tools-extra/',
                      defaultBranch='trunk',
                      workdir='%s/tools/clang/tools/extra' % llvm_srcdir))
        if checkout_compiler_rt:
            f.addStep(SVN(name='svn-compiler-rt',
                          mode='update',
                          baseURL='http://llvm.org/svn/llvm-project/compiler-rt/',
                          defaultBranch='trunk',
                          workdir='%s/projects/compiler-rt' % llvm_srcdir))

    # Clean up llvm (stage 1); unless in-dir.
    if clean and llvm_srcdir != llvm_1_objdir:
        f.addStep(ShellCommand(name="rm-llvm.obj.stage1",
                               command=["rm", "-rf", llvm_1_objdir],
                               haltOnFailure=True,
                               description=["rm build dir", "llvm"],
                               workdir=".",
                               env=merged_env))

    if not clean:
        expected_makefile = 'Makefile'
        f.addStep(SetProperty(name="Makefile_isready",
                              workdir=llvm_1_objdir,
                              command=["sh", "-c",
                                       "test -e %s && echo OK || echo Missing" % expected_makefile],
                              flunkOnFailure=False,
                              property="exists_Makefile"))

    cmake_triple_arg = []
    if triple:
        cmake_triple_arg = ['-DLLVM_HOST_TRIPLE=%s' % triple]
    f.addStep(ShellCommand(name='cmake',
                           command=['cmake',
                                    '-DLLVM_BUILD_TESTS=ON',
                                    '-DCMAKE_BUILD_TYPE=%s' % stage1_config] +
                                   cmake_triple_arg +
                                   extra_configure_args +
                                   ["../" + llvm_srcdir],
                           description='cmake stage1',
                           workdir=llvm_1_objdir,
                           env=merged_env,
                           doStepIf=lambda step: step.build.getProperty("exists_Makefile") != "OK"))

    # Make clean if using in-dir builds.
    if clean and llvm_srcdir == llvm_1_objdir:
        f.addStep(WarningCountingShellCommand(name="clean-llvm",
                                              command=[make, "clean"],
                                              haltOnFailure=True,
                                              description="cleaning llvm",
                                              descriptionDone="clean llvm",
                                              workdir=llvm_1_objdir,
                                              doStepIf=clean,
                                              env=merged_env))

    if extra_clean_step:
        f.addStep(extra_clean_step)

    f.addStep(WarningCountingShellCommand(name="compile",
                                          command=['nice', '-n', '10',
                                                   make, WithProperties("-j%s" % jobs)],
                                          haltOnFailure=True,
                                          flunkOnFailure=not run_gdb,
                                          description=["compiling", stage1_config],
                                          descriptionDone=["compile", stage1_config],
                                          workdir=llvm_1_objdir,
                                          env=merged_env))

    if examples:
        f.addStep(WarningCountingShellCommand(name="compile.examples",
                                              command=['nice', '-n', '10',
                                                       make, WithProperties("-j%s" % jobs),
                                                       "BUILD_EXAMPLES=1"],
                                              haltOnFailure=True,
                                              description=["compiling", stage1_config, "examples"],
                                              descriptionDone=["compile", stage1_config, "examples"],
                                              workdir=llvm_1_objdir,
                                              env=merged_env))

    clangTestArgs = '-v -j %s' % jobs
    if valgrind:
        clangTestArgs += ' --vg'
        if valgrindLeakCheck:
            clangTestArgs += ' --vg-leak'
        clangTestArgs += ' --vg-arg --suppressions=%(builddir)s/llvm/tools/clang/utils/valgrind/x86_64-pc-linux-gnu_gcc-4.3.3.supp --vg-arg --suppressions=%(builddir)s/llvm/utils/valgrind/x86_64-pc-linux-gnu.supp'
    extraTestDirs = ''
    if run_cxx_tests:
        extraTestDirs += '%(builddir)s/llvm/tools/clang/utils/C++Tests'
    if test:
        f.addStep(lit_test_command.LitTestCommand(name='check-all',
                                   command=[make, "check-all", "VERBOSE=1",
                                            WithProperties("LIT_ARGS=%s" % clangTestArgs),
                                            WithProperties("EXTRA_TESTDIRS=%s" % extraTestDirs)],
                                   flunkOnFailure=not run_gdb,
                                   description=["checking"],
                                   descriptionDone=["checked"],
                                   workdir=llvm_1_objdir,
                                   usePTY=use_pty_in_tests,
                                   env=merged_env))

    # TODO: Install llvm and clang for stage1.

    if run_gdb or run_gcc or run_modern_gdb:
        ignores = getClangTestsIgnoresFromPath(os.path.expanduser('~/public/clang-tests'), 'clang-x86_64-darwin10')
        install_prefix = "%%(builddir)s/%s" % llvm_1_installdir
        if run_gdb:
            addClangGDBTests(f, ignores, install_prefix)
        if run_modern_gdb:
            addModernClangGDBTests(f, jobs, install_prefix)
        if run_gcc:
            addClangGCCTests(f, ignores, install_prefix)

    if not useTwoStage:
        if package_dst:
            name = WithProperties(
                "%(builddir)s/" + llvm_1_objdir +
                "/clang-r%(got_revision)s-b%(buildnumber)s.tgz")
            f.addStep(ShellCommand(name='pkg.tar',
                                   description="tar root",
                                   command=["tar", "zcvf", name, "./"],
                                   workdir=llvm_1_installdir,
                                   warnOnFailure=True,
                                   flunkOnFailure=False,
                                   haltOnFailure=False,
                                   env=merged_env))
            f.addStep(ShellCommand(name='pkg.upload',
                                   description="upload root",
                                   command=["scp", name,
                                            WithProperties(
                            package_dst + "/%(buildername)s")],
                                   workdir=".",
                                   warnOnFailure=True,
                                   flunkOnFailure=False,
                                   haltOnFailure=False,
                                   env=merged_env))

        return f

    # Clean up llvm (stage 2).
    #
    # We always cleanly build the stage 2. If the compiler has been
    # changed on the stage 1, we cannot trust any of the intermediate file
    # from the old compiler. And if the stage 1 compiler is the same, we should
    # not build in the first place.
    f.addStep(ShellCommand(name="rm-llvm.obj.stage2",
                           command=["rm", "-rf", llvm_2_objdir],
                           haltOnFailure=True,
                           description=["rm build dir", "llvm", "(stage 2)"],
                           workdir=".",
                           env=merged_env))

    # Configure llvm (stage 2).
    f.addStep(ShellCommand(name='cmake',
                           command=['cmake'] + stage2_extra_configure_args + [
                                    '-DLLVM_BUILD_TESTS=ON',
                                    WithProperties('-DCMAKE_C_COMPILER=%%(builddir)s/%s/bin/clang' % llvm_1_objdir), # FIXME use installdir
                                    WithProperties('-DCMAKE_CXX_COMPILER=%%(builddir)s/%s/bin/clang++' % llvm_1_objdir),
                                    '-DCMAKE_BUILD_TYPE=%s' % stage2_config,
                                    "../" + llvm_srcdir],
                           description='cmake stage2',
                           workdir=llvm_2_objdir,
                           env=merged_env))

    # Build llvm (stage 2).
    f.addStep(WarningCountingShellCommand(name="compile.llvm.stage2",
                                          command=['nice', '-n', '10',
                                                   make, WithProperties("-j%s" % jobs)],
                                          haltOnFailure=True,
                                          description=["compiling", "(stage 2)",
                                                       stage2_config],
                                          descriptionDone=["compile", "(stage 2)",
                                                           stage2_config],
                                          workdir=llvm_2_objdir,
                                          env=merged_env))

    if test:
        f.addStep(lit_test_command.LitTestCommand(name='check-all',
                                   command=[make, "check-all", "VERBOSE=1",
                                            WithProperties("LIT_ARGS=%s" % clangTestArgs),
                                            WithProperties("EXTRA_TESTDIRS=%s" % extraTestDirs)],
                                   description=["checking"],
                                   descriptionDone=["checked"],
                                   workdir=llvm_2_objdir,
                                   usePTY=use_pty_in_tests,
                                   env=merged_env))

    # TODO: Install llvm and clang for stage2.

    if package_dst:
        name = WithProperties(
            "%(builddir)s/" + llvm_2_objdir +
            "/clang-r%(got_revision)s-b%(buildnumber)s.tgz")
        f.addStep(ShellCommand(name='pkg.tar',
                               description="tar root",
                               command=["tar", "zcvf", name, "./"],
                               workdir=llvm_2_installdir,
                               warnOnFailure=True,
                               flunkOnFailure=False,
                               haltOnFailure=False,
                               env=merged_env))
        f.addStep(ShellCommand(name='pkg.upload',
                               description="upload root",
                               command=["scp", name,
                                        WithProperties(
                        package_dst + "/%(buildername)s")],
                               workdir=".",
                               warnOnFailure=True,
                               flunkOnFailure=False,
                               haltOnFailure=False,
                               env=merged_env))

    return f

def addGCSUploadSteps(f, package_name, install_prefix, gcs_directory, env,
                      gcs_url_property=None, use_pixz_compression=False,
                      xz_compression_factor=6):
    """
    Add steps to upload to the Google Cloud Storage bucket.

    f - The BuildFactory to modify.
    package_name - The name of this package for the descriptions (e.g.
                   'stage 1')
    install_prefix - The directory the build has been installed to.
    gcs_directory - The subdirectory of the bucket root to upload to. This
                    should match the builder name.
    env - The environment to use. Set BOTO_CONFIG to use a configuration file
          in a non-standard location, and BUCKET to use a different GCS bucket.
    gcs_url_property - Property to assign the GCS url to.
    """

    gcs_url_fmt = ('gs://%(gcs_bucket)s/%(gcs_directory)s/'
                   'clang-r%(got_revision)s-t%(now)s-b%(buildnumber)s.tar.xz')
    time_fmt = '%Y-%m-%d_%H-%M-%S'
    output_file_name = '../install.tar.xz'

    gcs_url = \
        WithProperties(
            gcs_url_fmt,
            gcs_bucket=lambda _: env.get('BUCKET', 'llvm-build-artifacts'),
            gcs_directory=lambda _: gcs_directory,
            now=lambda _: datetime.utcnow().strftime(time_fmt))

    if gcs_url_property:
        f.addStep(SetProperty(
                      name="record GCS url for " + package_name,
                      command=['echo', gcs_url],
                      property=gcs_url_property))

    if use_pixz_compression:
        # tweak the xz compression level to generate packages faster
        tar_command = ['tar', '-Ipixz', '-cvf', output_file_name, '.']
    else:
        xz_command = 'xz -{0}'.format(xz_compression_factor)
        tar_command = ['tar', '-I', xz_command, '-cvf', output_file_name, '.']

    f.addStep(ShellCommand(name='package ' + package_name,
                           command=tar_command,
                           description='packaging ' + package_name + '...',
                           workdir=install_prefix,
                           env=env))

    f.addStep(ShellCommand(
                  name='upload ' + package_name + ' to storage bucket',
                  command=['gsutil', 'cp', '../install.tar.xz', gcs_url],
                  description=('uploading ' + package_name +
                               'to storage bucket ...'),
                  workdir=install_prefix,
                  env=env))

def getClangCMakeGCSBuildFactory(
            clean=True,
            test=True,
            cmake='cmake',
            jobs=None,

            # VS tools environment variable if using MSVC. For example,
            # %VS120COMNTOOLS% selects the 2013 toolchain.
            vs=None,
            vs_target_arch='x86',

            # Multi-stage compilation
            useTwoStage=False,
            testStage1=True,
            stage1_config='Release',
            stage2_config='Release',

            # Test-suite
            runTestSuite=False,
            nt_flags=[],
            testsuite_flags=[],
            submitURL=None,
            testerName=None,

            # Environmental variables for all steps.
            env={},
            extra_cmake_args=[],

            # Extra repositories
            checkout_clang_tools_extra=True,
            checkout_compiler_rt=True,
            checkout_lld=True,
            checkout_libcxx=False,

            # Upload artifacts to Google Cloud Storage (for the llvmbisect tool)
            stage1_upload_directory=None,

            # Use a lower compression level to generate the build-cache package faster.
            # defuault is 6 according to xz documentation
            xz_compression_factor=6,
            use_pixz_compression=False,

            # Triggers
            trigger_after_stage1=[]):
    return _getClangCMakeBuildFactory(
               clean=clean, test=test, cmake=cmake, jobs=jobs, vs=vs,
               vs_target_arch=vs_target_arch, useTwoStage=useTwoStage,
               testStage1=testStage1, stage1_config=stage1_config,
               stage2_config=stage2_config, runTestSuite=runTestSuite,
               nt_flags=nt_flags, testsuite_flags=testsuite_flags,
               submitURL=submitURL, testerName=testerName,
               env=env, extra_cmake_args=extra_cmake_args,
               checkout_clang_tools_extra=checkout_clang_tools_extra,
               checkout_compiler_rt=checkout_compiler_rt,
               checkout_lld=checkout_lld,
               checkout_libcxx=checkout_libcxx,
               stage1_upload_directory=stage1_upload_directory,
               xz_compression_factor=xz_compression_factor,
               use_pixz_compression=use_pixz_compression,
               trigger_after_stage1=trigger_after_stage1)

def getClangCMakeBuildFactory(
            clean=True,
            test=True,
            cmake='cmake',
            jobs=None,

            # VS tools environment variable if using MSVC. For example,
            # %VS120COMNTOOLS% selects the 2013 toolchain.
            vs=None,
            vs_target_arch='x86',

            # Multi-stage compilation
            useTwoStage=False,
            testStage1=True,
            stage1_config='Release',
            stage2_config='Release',

            # Test-suite
            runTestSuite=False,
            nt_flags=[],
            testsuite_flags=[],
            submitURL=None,
            testerName=None,

            # Environmental variables for all steps.
            env={},
            extra_cmake_args=[],

            # Extra repositories
            checkout_clang_tools_extra=True,
            checkout_compiler_rt=True,
            checkout_lld=True,
            checkout_libcxx=False,
            checkout_test_suite=False):
    return _getClangCMakeBuildFactory(
               clean=clean, test=test, cmake=cmake, jobs=jobs, vs=vs,
               vs_target_arch=vs_target_arch, useTwoStage=useTwoStage,
               testStage1=testStage1, stage1_config=stage1_config,
               stage2_config=stage2_config, runTestSuite=runTestSuite,
               nt_flags=nt_flags, testsuite_flags=testsuite_flags,
               submitURL=submitURL, testerName=testerName,
               env=env, extra_cmake_args=extra_cmake_args,
               checkout_clang_tools_extra=checkout_clang_tools_extra,
               checkout_lld=checkout_lld,
               checkout_compiler_rt=checkout_compiler_rt,
               checkout_libcxx=checkout_libcxx,
               checkout_test_suite=checkout_test_suite)

def _getClangCMakeBuildFactory(
            clean=True,
            test=True,
            cmake='cmake',
            jobs=None,

            # VS tools environment variable if using MSVC. For example,
            # %VS120COMNTOOLS% selects the 2013 toolchain.
            vs=None,
            vs_target_arch='x86',

            # Multi-stage compilation
            useTwoStage=False,
            testStage1=True,
            stage1_config='Release',
            stage2_config='Release',

            # Test-suite
            runTestSuite=False,
            nt_flags=[],
            testsuite_flags=[],
            submitURL=None,
            testerName=None,

            # Environmental variables for all steps.
            env={},
            extra_cmake_args=[],

            # Extra repositories
            checkout_clang_tools_extra=True,
            checkout_compiler_rt=True,
            checkout_lld=True,
            checkout_libcxx=False,
            checkout_test_suite=False,

            # Upload artifacts to Google Cloud Storage (for the llvmbisect tool)
            stage1_upload_directory=None,

            # Use a lower compression level to generate the build-cache package faster
            # default is 6 according to documentation
            xz_compression_factor=6,
            use_pixz_compression=False,

            # Triggers
            trigger_after_stage1=[]):

    ############# PREPARING
    clean_build_requested = lambda step: \
        step.build.getProperty( \
            "clean", \
            default=step.build.getProperty("clean_obj") \
        ) or clean

    # We *must* checkout at least Clang+LLVM
    depends_on_projects = ['llvm', 'clang']
    if checkout_clang_tools_extra:
        depends_on_projects.append('clang-tools-extra')
    if checkout_compiler_rt:
        depends_on_projects.append('compiler-rt')
    if checkout_lld:
        depends_on_projects.append('lld')
    if runTestSuite or checkout_test_suite:
        depends_on_projects.append('lnt')
        depends_on_projects.append('test-suite')
    if checkout_libcxx:
        depends_on_projects.append('libcxx')
        depends_on_projects.append('libcxxabi')
        depends_on_projects.append('libunwind')

    f = LLVMBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir='llvm')

    f.addSVNSteps()

    # If jobs not defined, Ninja will choose a suitable value
    jobs_cmd = []
    lit_args = "'-v"
    if jobs is not None:
        jobs_cmd = ["-j"+str(jobs)]
        lit_args += " -j"+str(jobs)+"'"
    else:
        lit_args += "'"
    ninja_cmd = ['ninja'] + jobs_cmd
    ninja_install_cmd = ['ninja', 'install'] + jobs_cmd
    ninja_check_cmd = ['ninja', 'check-all'] + jobs_cmd

    # Global configurations
    stage1_build = 'stage1'
    stage1_install = 'stage1.install'
    stage2_build = 'stage2'
    stage2_install = 'stage2.install'

    # Set up VS environment, if appropriate.
    if vs:
        f.addStep(SetProperty(
            command=builders_util.getVisualStudioEnvironment(vs, vs_target_arch),
            extract_fn=builders_util.extractSlaveEnvironment))
        assert not env, "Can't have custom builder env vars with VS"
        env = Property('slave_env')


    ############# CLEANING
    f.addStep(ShellCommand(name='clean stage 1',
                           command=['rm','-rf',stage1_build],
                           warnOnFailure=True,
                           haltOnFailure=False,
                           flunkOnFailure=False,
                           description='cleaning stage 1',
                           descriptionDone='clean',
                           workdir='.',
                           doStepIf=clean_build_requested))


    ############# STAGE 1
    f.addStep(ShellCommand(name='cmake stage 1',
                           command=[cmake, "-G", "Ninja", "../llvm",
                                    "-DCMAKE_BUILD_TYPE="+stage1_config,
                                    "-DLLVM_ENABLE_ASSERTIONS=True",
                                    "-DLLVM_LIT_ARGS="+lit_args,
                                    "-DCMAKE_INSTALL_PREFIX=../"+stage1_install]
                                    + extra_cmake_args,
                           haltOnFailure=True,
                           description='cmake stage 1',
                           workdir=stage1_build,
                           doStepIf=FileDoesNotExist("build.ninja"),
                           env=env))

    f.addStep(WarningCountingShellCommand(name='build stage 1',
                                          command=ninja_cmd,
                                          haltOnFailure=True,
                                          description='ninja all',
                                          workdir=stage1_build,
                                          env=env))

    if test and testStage1:
        haltOnStage1Check = not useTwoStage and not runTestSuite
        f.addStep(lit_test_command.LitTestCommand(name='ninja check 1',
                                   command=ninja_check_cmd,
                                   haltOnFailure=haltOnStage1Check,
                                   description=["checking stage 1"],
                                   descriptionDone=["stage 1 checked"],
                                   workdir=stage1_build,
                                   env=env))

    if useTwoStage or runTestSuite or stage1_upload_directory:
        f.addStep(ShellCommand(name='clean stage 1 install',
                               command=['rm','-rf',stage1_install],
                               warnOnFailure=True,
                               haltOnFailure=False,
                               flunkOnFailure=False,
                               description='cleaning stage 1 install',
                               descriptionDone='clean',
                               workdir='.'))
        f.addStep(ShellCommand(name='install stage 1',
                               command=ninja_install_cmd,
                               description='ninja install',
                               workdir=stage1_build,
                               env=env))

    if stage1_upload_directory:
        addGCSUploadSteps(f, 'stage 1', stage1_install, stage1_upload_directory,
                          env, gcs_url_property='stage1_package_gcs_url',
                          use_pixz_compression=use_pixz_compression,
                          xz_compression_factor=xz_compression_factor)

    # Compute the cmake define flag to set the C and C++ compiler to clang. Use
    # clang-cl if we used MSVC for stage1.
    if not vs:
        cc = 'clang'
        cxx = 'clang++'
    else:
        cc = 'clang-cl.exe'
        cxx = 'clang-cl.exe'


    ############# STAGE 2
    if useTwoStage:
        # We always cleanly build the stage 2. If the compiler has been
        # changed on the stage 1, we cannot trust any of the intermediate file
        # from the old compiler. And if the stage 1 compiler is the same, we
        # should not build in the first place.
        f.addStep(ShellCommand(name='clean stage 2',
                               command=['rm','-rf',stage2_build],
                               warnOnFailure=True,
                               description='cleaning stage 2',
                               descriptionDone='clean',
                               workdir='.'))

        # Set the compiler using the CC and CXX environment variables to work around
        # backslash string escaping bugs somewhere between buildbot and cmake. The
        # env.exe helper is required to run the tests, so hopefully it's already on
        # PATH.
        cmake_cmd2 = ['env',
                      WithProperties('CC=%(workdir)s/'+stage1_install+'/bin/'+cc),
                      WithProperties('CXX=%(workdir)s/'+stage1_install+'/bin/'+cxx),
                      cmake, "-G", "Ninja", "../llvm",
                      "-DCMAKE_BUILD_TYPE="+stage2_config,
                      "-DLLVM_ENABLE_ASSERTIONS=True",
                      "-DLLVM_LIT_ARGS="+lit_args,
                      "-DCMAKE_INSTALL_PREFIX=../"+stage2_install] + extra_cmake_args

        f.addStep(ShellCommand(name='cmake stage 2',
                               command=cmake_cmd2,
                               haltOnFailure=True,
                               description='cmake stage 2',
                               workdir=stage2_build,
                               env=env))

        f.addStep(WarningCountingShellCommand(name='build stage 2',
                                              command=ninja_cmd,
                                              haltOnFailure=True,
                                              description='ninja all',
                                              workdir=stage2_build,
                                              env=env))

        if test:
            f.addStep(lit_test_command.LitTestCommand(name='ninja check 2',
                                       command=ninja_check_cmd,
                                       haltOnFailure=not runTestSuite,
                                       description=["checking stage 2"],
                                       descriptionDone=["stage 2 checked"],
                                       workdir=stage2_build,
                                       env=env))

    ############# TEST SUITE
    ## Test-Suite (stage 2 if built, stage 1 otherwise)
    if runTestSuite:
        compiler_path = stage1_install
        if useTwoStage:
            compiler_path=stage2_install
            f.addStep(ShellCommand(name='clean stage 2 install',
                                   command=['rm','-rf',stage2_install],
                                   warnOnFailure=True,
                                   description='cleaning stage 2 install',
                                   descriptionDone='clean',
                                   workdir='.'))
            f.addStep(ShellCommand(name='install stage 2',
                                   command=ninja_install_cmd,
                                   description='ninja install 2',
                                   workdir=stage2_build,
                                   env=env))

        # Get generated python, lnt
        python = WithProperties('%(workdir)s/test/sandbox/bin/python')
        lnt = WithProperties('%(workdir)s/test/sandbox/bin/lnt')
        lnt_setup = WithProperties('%(workdir)s/test/lnt/setup.py')

        # Paths
        sandbox = WithProperties('%(workdir)s/test/sandbox')
        test_suite_dir = WithProperties('%(workdir)s/test/test-suite')

        # Get latest built Clang (stage1 or stage2)
        cc = WithProperties('%(workdir)s/'+compiler_path+'/bin/'+cc)
        cxx = WithProperties('%(workdir)s/'+compiler_path+'/bin/'+cxx)

        # LNT Command line (don't pass -jN. Users need to pass both --threads
        # and --build-threads in nt_flags/test_suite_flags to get the same effect)
        use_runtest_testsuite = len(nt_flags) == 0
        if not use_runtest_testsuite:
            test_suite_cmd = [python, lnt, 'runtest', 'nt',
                              '--no-timestamp',
                              '--sandbox', sandbox,
                              '--test-suite', test_suite_dir,
                              '--cc', cc,
                              '--cxx', cxx]
            # Append any option provided by the user
            test_suite_cmd.extend(nt_flags)
        else:
            lit = WithProperties('%(workdir)s/'+stage1_build+'/bin/llvm-lit')
            test_suite_cmd = [python, lnt, 'runtest', 'test-suite',
                              '--no-timestamp',
                              '--sandbox', sandbox,
                              '--test-suite', test_suite_dir,
                              '--cc', cc,
                              '--cxx', cxx,
                              '--use-lit', lit]
            # Append any option provided by the user
            test_suite_cmd.extend(testsuite_flags)

        # Only submit if a URL has been specified
        if submitURL is not None:
            if not isinstance(submitURL, list):
                submitURL = [submitURL]
            for url in submitURL:
                test_suite_cmd.extend(['--submit', url])
            # lnt runtest test-suite doesn't understand --no-machdep-info:
            if testerName and not use_runtest_testsuite:
                test_suite_cmd.extend(['--no-machdep-info', testerName])
        # CC and CXX are needed as env for build-tools
        test_suite_env = copy.deepcopy(env)
        test_suite_env['CC'] = cc
        test_suite_env['CXX'] = cxx

        # Steps to prepare, build and run LNT
        f.addStep(ShellCommand(name='clean sandbox',
                               command=['rm', '-rf', 'sandbox'],
                               haltOnFailure=True,
                               description='removing sandbox directory',
                               workdir='test',
                               env=env))
        f.addStep(ShellCommand(name='recreate sandbox',
                               command=['virtualenv', 'sandbox'],
                               haltOnFailure=True,
                               description='recreating sandbox',
                               workdir='test',
                               env=env))
        f.addStep(ShellCommand(name='setup lit',
                               command=[python, lnt_setup, 'develop'],
                               haltOnFailure=True,
                               description='setting up LNT in sandbox',
                               workdir='test/sandbox',
                               env=env))
        f.addStep(commands.LitTestCommand.LitTestCommand(
                               name='test-suite',
                               command=test_suite_cmd,
                               haltOnFailure=True,
                               description=['running the test suite'],
                               workdir='test/sandbox',
                               logfiles={'configure.log'   : 'build/configure.log',
                                         'build-tools.log' : 'build/build-tools.log',
                                         'test.log'        : 'build/test.log',
                                         'report.json'     : 'build/report.json'},
                               env=test_suite_env))

    return f

def addClangGCCTests(f, ignores={}, install_prefix="%(builddir)s/llvm.install",
                     languages = ('gcc', 'g++', 'objc', 'obj-c++')):
    make_vars = [WithProperties(
            'CC_UNDER_TEST=%s/bin/clang' % install_prefix),
                 WithProperties(
            'CXX_UNDER_TEST=%s/bin/clang++' % install_prefix)]
    f.addStep(SVN(name='svn-clang-gcc-tests', mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/clang-tests/',
                  defaultBranch='trunk', workdir='clang-tests'))
    gcc_dg_ignores = ignores.get('gcc-4_2-testsuite', {})
    for lang in languages:
        f.addStep(commands.SuppressionDejaGNUCommand.SuppressionDejaGNUCommand(
            name='test-gcc-4_2-testsuite-%s' % lang,
            command=["make", "-k", "check-%s" % lang] + make_vars,
            description="gcc-4_2-testsuite (%s)" % lang,
            workdir='clang-tests/gcc-4_2-testsuite',
            logfiles={ 'dg.sum' : 'obj/%s/%s.sum' % (lang, lang),
                       '%s.log' % lang : 'obj/%s/%s.log' % (lang, lang)},
            ignore=gcc_dg_ignores.get(lang, [])))

def addClangGDBTests(f, ignores={}, install_prefix="%(builddir)s/llvm.install"):
    make_vars = [WithProperties(
            'CC_UNDER_TEST=%s/bin/clang' % install_prefix),
                 WithProperties(
            'CXX_UNDER_TEST=%s/bin/clang++' % install_prefix)]
    f.addStep(SVN(name='svn-clang-gdb-tests', mode='update',
                  baseURL='http://llvm.org/svn/llvm-project/clang-tests/',
                  defaultBranch='trunk', workdir='clang-tests'))
    f.addStep(commands.SuppressionDejaGNUCommand.SuppressionDejaGNUCommand(
            name='test-gdb-1472-testsuite',
            command=["make", "-k", "check"] + make_vars,
            description="gdb-1472-testsuite",
            workdir='clang-tests/gdb-1472-testsuite',
            logfiles={ 'dg.sum' : 'obj/filtered.gdb.sum',
                       'gdb.log' : 'obj/gdb.log' }))

def addModernClangGDBTests(f, jobs, install_prefix):
    make_vars = [WithProperties('RUNTESTFLAGS=CC_FOR_TARGET=\'{0}/bin/clang\' '
                                'CXX_FOR_TARGET=\'{0}/bin/clang++\' '
                                'CFLAGS_FOR_TARGET=\'-w -fno-limit-debug-info\''
                                .format(install_prefix))]
    f.addStep(SVN(name='svn-clang-modern-gdb-tests', mode='update',
                  svnurl='http://llvm.org/svn/llvm-project/clang-tests-external/trunk/gdb/7.5',
                  workdir='clang-tests/src'))
    f.addStep(Configure(command='../src/configure',
                        workdir='clang-tests/build/'))
    f.addStep(WarningCountingShellCommand(name='gdb-75-build',
                                          command=['make', WithProperties('-j%s' % jobs)],
                                          haltOnFailure=True,
                                          workdir='clang-tests/build'))
    f.addStep(commands.DejaGNUCommand.DejaGNUCommand(
            name='gdb-75-check',
            command=['make', '-k', WithProperties('-j%s' % jobs), 'check'] + make_vars,
            workdir='clang-tests/build',
            logfiles={'dg.sum':'gdb/testsuite/gdb.sum', 
                      'gdb.log':'gdb/testsuite/gdb.log'}))



# FIXME: Deprecated.
addClangTests = addClangGCCTests

def getClangTestsIgnoresFromPath(path, key):
    def readList(path):
        if not os.path.exists(path):
            return []

        f = open(path)
        lines = [ln.strip() for ln in f]
        f.close()
        return lines

    ignores = {}

    gcc_dg_ignores = {}
    for lang in ('gcc', 'g++', 'objc', 'obj-c++'):
        lang_path = os.path.join(path, 'gcc-4_2-testsuite', 'expected_results',
                                 key, lang)
        gcc_dg_ignores[lang] = (
            readList(os.path.join(lang_path, 'FAIL.txt')) +
            readList(os.path.join(lang_path, 'UNRESOLVED.txt')) +
            readList(os.path.join(lang_path, 'XPASS.txt')))
    ignores['gcc-4_2-testsuite' ] = gcc_dg_ignores

    ignores_path = os.path.join(path, 'gdb-1472-testsuite', 'expected_results',
                                key)
    gdb_dg_ignores = (
        readList(os.path.join(ignores_path, 'FAIL.txt')) +
        readList(os.path.join(ignores_path, 'UNRESOLVED.txt')) +
        readList(os.path.join(ignores_path, 'XPASS.txt')))
    ignores['gdb-1472-testsuite' ] = gdb_dg_ignores

    return ignores
