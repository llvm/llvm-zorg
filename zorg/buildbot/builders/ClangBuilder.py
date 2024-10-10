import copy
from datetime import datetime

from buildbot.plugins import util
from buildbot.steps.shell import ShellCommand, SetProperty
from buildbot.steps.shell import WarningCountingShellCommand

import zorg.buildbot.builders.Util as builders_util

from zorg.buildbot.commands.LitTestCommand import LitTestCommand
from zorg.buildbot.conditions.FileConditions import FileDoesNotExist
from zorg.buildbot.commands.CmakeCommand import CmakeCommand
from zorg.buildbot.process.properties import InterpolateToPosixPath
from zorg.buildbot.process.factory import LLVMBuildFactory

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

    gcs_url_fmt = ('gs://%(kw:gcs_bucket)s/%(kw:gcs_directory)s/'
                   'clang-r%(prop:got_revision)s-t%(kw:now)s-b%(prop:buildnumber)s.tar.xz')
    time_fmt = '%Y-%m-%d_%H-%M-%S'
    output_file_name = '../install.tar.xz'

    gcs_url = \
        util.Interpolate(
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
        xz_command = f'xz -{xz_compression_factor}'
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
            checks=None,
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
            nt_flags=None,
            testsuite_flags=None,
            submitURL=None,
            testerName=None,

            # Environmental variables for all steps.
            env=None,
            extra_cmake_args=None,

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
            trigger_after_stage1=None):
    return _getClangCMakeBuildFactory(
               clean=clean, checks=checks, cmake=cmake, jobs=jobs, vs=vs,
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
            checks=None,
            cmake='cmake',
            jobs=None,
            timeout=None, # TODO: Implement support for timeout

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
            nt_flags=None,
            testsuite_flags=None,
            submitURL=None,
            testerName=None,

            # Environmental variables for all steps.
            env=None,
            extra_cmake_args=None,

            # CMake arguments to use for stage2 instead of extra_cmake_args.
            extra_stage2_cmake_args=None,

            # Extra repositories
            checkout_clang_tools_extra=True,
            checkout_compiler_rt=True,
            checkout_lld=True,
            checkout_libcxx=False,
            checkout_flang=False,
            checkout_test_suite=False,

            enable_runtimes="auto"):
    return _getClangCMakeBuildFactory(
               clean=clean, checks=checks, cmake=cmake, jobs=jobs, vs=vs,
               vs_target_arch=vs_target_arch, useTwoStage=useTwoStage,
               testStage1=testStage1, stage1_config=stage1_config,
               stage2_config=stage2_config, runTestSuite=runTestSuite,
               nt_flags=nt_flags, testsuite_flags=testsuite_flags,
               submitURL=submitURL, testerName=testerName,
               env=env, extra_cmake_args=extra_cmake_args,
               extra_stage2_cmake_args=extra_stage2_cmake_args,
               checkout_clang_tools_extra=checkout_clang_tools_extra,
               checkout_lld=checkout_lld,
               checkout_compiler_rt=checkout_compiler_rt,
               checkout_libcxx=checkout_libcxx,
               checkout_flang=checkout_flang,
               checkout_test_suite=checkout_test_suite,
               enable_runtimes=enable_runtimes)

def _getClangCMakeBuildFactory(
            clean=True,
            checks=None,
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
            nt_flags=None,
            testsuite_flags=None,
            submitURL=None,
            testerName=None,

            # Environmental variables for all steps.
            env=None,
            extra_cmake_args=None,

            # CMake arguments to use for stage2 instead of extra_cmake_args.
            extra_stage2_cmake_args=None,

            # Extra repositories
            checkout_clang_tools_extra=True,
            checkout_compiler_rt=True,
            checkout_lld=True,
            checkout_libcxx=False,
            checkout_test_suite=False,
            checkout_flang=False,

            enable_runtimes="auto",

            # Upload artifacts to Google Cloud Storage (for the llvmbisect tool)
            stage1_upload_directory=None,

            # Use a lower compression level to generate the build-cache package faster
            # default is 6 according to documentation
            xz_compression_factor=6,
            use_pixz_compression=False,

            # Triggers
            trigger_after_stage1=None):

    ############# PREPARING
    if checks is None:
        checks = ['check-all']
    if nt_flags is None:
        nt_flags = []
    if testsuite_flags is None:
        testsuite_flags = []
    if env is None:
        env = {}
    if extra_cmake_args is None:
        extra_cmake_args = []
    if trigger_after_stage1 is None:
        trigger_after_stage1 = []

    clean_build_requested = lambda step: \
        step.build.getProperty("clean") \
        or step.build.getProperty("clean_obj") \
        or clean

    # We *must* checkout at least Clang+LLVM
    depends_on_projects = ['llvm', 'clang']
    if checkout_clang_tools_extra:
        depends_on_projects.append('clang-tools-extra')
    if checkout_compiler_rt:
        depends_on_projects.append('compiler-rt')
    if checkout_lld:
        depends_on_projects.append('lld')
    if checkout_libcxx:
        depends_on_projects.append('libcxx')
        depends_on_projects.append('libcxxabi')
        depends_on_projects.append('libunwind')
    if checkout_flang:
        depends_on_projects.append('flang')
        depends_on_projects.append('mlir')

    f = LLVMBuildFactory(
            depends_on_projects=depends_on_projects,
            llvm_srcdir='llvm',
            enable_runtimes=enable_runtimes,
            clean=clean)

    # Checkout the latest code for LNT
    # and the test-suite separately. Le's do this first,
    # so we wouldn't poison got_revision property.
    if runTestSuite or checkout_test_suite:
        f.addGetSourcecodeForProject(
            project='lnt',
            src_dir='test/lnt',
            alwaysUseLatest=True)
        f.addGetSourcecodeForProject(
            project='test-suite',
            src_dir='test/test-suite',
            alwaysUseLatest=True)

    # Then get the LLVM source code revision this particular build is for.
    f.addGetSourcecodeSteps()

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
    ninja_check_cmd = ['ninja'] + checks + jobs_cmd

    # Global configurations
    stage1_build = 'stage1'
    stage1_install = 'stage1.install'
    stage2_build = 'stage2'
    stage2_install = 'stage2.install'

    # Set up VS environment, if appropriate.
    if vs and vs != "manual":
        f.addStep(SetProperty(
            command=builders_util.getVisualStudioEnvironment(vs, vs_target_arch),
            extract_fn=builders_util.extractVSEnvironment))
        assert not env, "Can't have custom builder env vars with VS"
        env = util.Property('vs_env')


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
    if f.enable_projects:
        CmakeCommand.applyRequiredOptions(extra_cmake_args, [
            ('-DLLVM_ENABLE_PROJECTS=', ";".join(f.enable_projects)),
            ])
    if f.enable_runtimes:
        CmakeCommand.applyRequiredOptions(extra_cmake_args, [
            ('-DLLVM_ENABLE_RUNTIMES=', ";".join(f.enable_runtimes)),
            ])

    rel_src_dir = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, stage1_build)

    f.addStep(ShellCommand(name='cmake stage 1',
                           command=[cmake, "-G", "Ninja", rel_src_dir,
                                    "-DCMAKE_BUILD_TYPE="+stage1_config,
                                    "-DLLVM_ENABLE_ASSERTIONS=True",
                                    "-DLLVM_LIT_ARGS="+lit_args,
                                    f"-DCMAKE_INSTALL_PREFIX=../{stage1_install}"]
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

    if checks and testStage1:
        haltOnStage1Check = not useTwoStage and not runTestSuite
        f.addStep(LitTestCommand(name='ninja check 1',
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
        fc = 'flang-new'
    else:
        cc = 'clang-cl.exe'
        cxx = 'clang-cl.exe'
        fc = 'flang-new.exe'


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

        # Absolute paths to just built compilers.
        # Note: Backslash path separators do not work well with cmake and ninja.
        # Forward slash path separator works on Windows as well.
        stage1_cc = InterpolateToPosixPath(
                        f"-DCMAKE_C_COMPILER=%(prop:builddir)s/{stage1_install}/bin/{cc}")
        stage1_cxx = InterpolateToPosixPath(
                        f"-DCMAKE_CXX_COMPILER=%(prop:builddir)s/{stage1_install}/bin/{cxx}")

        # If we have a separate stage2 cmake arg list, then ensure we re-apply
        # enable_projects and enable_runtimes if necessary.
        if extra_stage2_cmake_args:
            if f.enable_projects:
                CmakeCommand.applyRequiredOptions(extra_stage2_cmake_args, [
                    ('-DLLVM_ENABLE_PROJECTS=', ";".join(f.enable_projects)),
                    ])
            if f.enable_runtimes:
                CmakeCommand.applyRequiredOptions(extra_stage2_cmake_args, [
                    ('-DLLVM_ENABLE_RUNTIMES=', ";".join(f.enable_runtimes)),
                    ])

        rel_src_dir = LLVMBuildFactory.pathRelativeTo(f.llvm_srcdir, stage2_build)
        cmake_cmd2 = [cmake, "-G", "Ninja", rel_src_dir,
                      stage1_cc,
                      stage1_cxx,
                      f"-DCMAKE_BUILD_TYPE={stage2_config}",
                      "-DLLVM_ENABLE_ASSERTIONS=True",
                      f"-DLLVM_LIT_ARGS={lit_args}",
                      f"-DCMAKE_INSTALL_PREFIX=../{stage2_install}"
                     ] + (extra_stage2_cmake_args or extra_cmake_args)

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

        if checks:
            f.addStep(LitTestCommand(name='ninja check 2',
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
        python = util.Interpolate('%(prop:builddir)s/test/sandbox/bin/python')
        lnt = util.Interpolate('%(prop:builddir)s/test/sandbox/bin/lnt')
        lnt_setup = util.Interpolate('%(prop:builddir)s/test/lnt/setup.py')

        # Paths
        sandbox = util.Interpolate('%(prop:builddir)s/test/sandbox')
        test_suite_dir = util.Interpolate('%(prop:builddir)s/test/test-suite')

        # Get latest built Clang (stage1 or stage2)
        cc = util.Interpolate(f'%(prop:builddir)s/{compiler_path}/bin/{cc}')
        cxx = util.Interpolate(f'%(prop:builddir)s/{compiler_path}/bin/{cxx}')

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
            lit = util.Interpolate(f'%(prop:builddir)s/{stage1_build}/bin/llvm-lit')
            test_suite_cmd = [python, lnt, 'runtest', 'test-suite',
                              '--no-timestamp',
                              '--sandbox', sandbox,
                              '--test-suite', test_suite_dir,
                              '--cc', cc,
                              '--cxx', cxx,
                              '--use-lit', lit,
                              # Carry on building even if there is a failure.
                              '--build-tool-options', '"-k"']
            # Enable fortran if flang is checked out
            if checkout_flang:
                fortran_flags = [
                        '--cmake-define=TEST_SUITE_FORTRAN:STRING=ON',
                        util.Interpolate(
                            '--cmake-define=CMAKE_Fortran_COMPILER=' +
                            f'%(prop:builddir)s/{compiler_path}/bin/{fc}')]
                test_suite_cmd.extend(fortran_flags)
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
        if vs and vs != "manual":
            # VS environment requires some extra care.
            f.addStep(SetProperty(
                command=builders_util.getVisualStudioEnvironment(vs, vs_target_arch),
                extract_fn=builders_util.extractVSEnvironment,
                env={'CC'  : cc, 'CXX' : cxx}))
            test_suite_env = Property('vs_env')
        else:
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
                               command=['virtualenv', '--python=python3', 'sandbox'],
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
        f.addStep(LitTestCommand(
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
