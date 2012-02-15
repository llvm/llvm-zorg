import csv
import os
import re
import shutil
import subprocess
import sys
import time
import traceback

from datetime import datetime

import lnt.testing
import lnt.testing.util.compilers

from lnt.testing.util.commands import note, warning, error, fatal
from lnt.testing.util.commands import capture, mkdir_p, which
from lnt.testing.util.rcs import get_source_version
from lnt.testing.util.misc import timestamp

###

class TestModule(object):
    """
    Base class for extension test modules.
    """

    def __init__(self):
        self._log = None

    def main(self):
        raise NotImplementedError

    def execute_test(self, options):
        abstract

    def _execute_test(self, test_log, options):
        self._log = test_log
        try:
            return self.execute_test(options)
        finally:
            self._log = None

    @property
    def log(self):
        """Get the test log output stream."""
        if self._log is None:
            raise ValueError("log() unavailable outside test execution")
        return self._log
        
###

def scan_for_test_modules(opts):
    base_modules_path = os.path.join(opts.test_suite_root, 'LNTBased')
    if opts.only_test is None:
        test_modules_path = base_modules_path
    elif opts.only_test.startswith('LNTBased'):
        test_modules_path = os.path.join(opts.test_suite_root, opts.only_test)
    else:
        return

    # We follow links here because we want to support the ability for having
    # various "suites" of LNTBased tests in separate repositories, and allowing
    # users to just checkout them out elsewhere and link them into their LLVM
    # test-suite source tree.
    for dirpath,dirnames,filenames in os.walk(test_modules_path,
                                              followlinks = True):
        # Ignore the example tests, unless requested.
        if not opts.include_test_examples and 'Examples' in dirnames:
            dirnames.remove('Examples')

        # Check if this directory defines a test module.
        if 'TestModule' not in filenames:
            continue

        # If so, don't traverse any lower.
        del dirnames[:]

        # Add to the list of test modules.
        assert dirpath.startswith(base_modules_path + '/')
        yield dirpath[len(base_modules_path) + 1:]

def execute_test_modules(test_log, test_modules, test_module_variables,
                         basedir, opts):
    # For now, we don't execute these in parallel, but we do forward the
    # parallel build options to the test.
    test_modules.sort()

    print >>sys.stderr, '%s: executing test modules' % (timestamp(),)
    results = []
    for name in test_modules:
        # First, load the test module file.
        locals = globals = {}
        test_path = os.path.join(opts.test_suite_root, 'LNTBased', name)
        test_obj_path = os.path.join(basedir, 'LNTBased', name)
        module_path = os.path.join(test_path, 'TestModule')
        module_file = open(module_path)
        try:
            exec module_file in locals, globals
        except:
            info = traceback.format_exc()
            fatal("unable to import test module: %r\n%s" % (
                    module_path, info))

        # Lookup and instantiate the test class.
        test_class = globals.get('test_class')
        if test_class is None:
            fatal("no 'test_class' global in import test module: %r" % (
                    module_path,))
        try:
            test_instance = test_class()
        except:
            fatal("unable to instantiate test class for: %r" % module_path)

        if not isinstance(test_instance, TestModule):
            fatal("invalid test class (expected lnt.tests.nt.TestModule "
                  "subclass) for: %r" % module_path)

        # Create the per test variables, and ensure the output directory exists.
        variables = test_module_variables.copy()
        variables['MODULENAME'] = name
        variables['SRCROOT'] = test_path
        variables['OBJROOT'] = test_obj_path
        mkdir_p(test_obj_path)

        # Execute the tests.
        try:
            test_samples = test_instance._execute_test(test_log, variables)
        except:
            info = traceback.format_exc()
            fatal("exception executing tests for: %r\n%s" % (
                    module_path, info))

        # Check that the test samples are in the expected format.
        is_ok = True
        try:
            test_samples = list(test_samples)
            for item in test_samples:
                if not isinstance(item, lnt.testing.TestSamples):
                    is_ok = False
                    break
        except:
            is_ok = False
        if not is_ok:
            fatal("test module did not return samples list: %r" % (
                    module_path,))

        results.append((name, test_samples))

    return results

def compute_test_module_variables(make_variables, opts):
    # Set the test module options, which we try and restrict to a tighter subset
    # than what we pass to the LNT makefiles.
    test_module_variables = {
        'CC' : make_variables['TARGET_LLVMGCC'],
        'CXX' : make_variables['TARGET_LLVMGXX'],
        'CFLAGS' : (make_variables['TARGET_FLAGS'] + ' ' +
                    make_variables['OPTFLAGS']),
        'CXXFLAGS' : (make_variables['TARGET_FLAGS'] + ' ' +
                      make_variables['OPTFLAGS']) }

    # Add the remote execution variables.
    if opts.remote:
        test_module_variables['REMOTE_HOST'] = make_variables['REMOTE_HOST']
        test_module_variables['REMOTE_USER'] = make_variables['REMOTE_USER']
        test_module_variables['REMOTE_PORT'] = make_variables['REMOTE_PORT']
        test_module_variables['REMOTE_CLIENT'] = make_variables['REMOTE_CLIENT']

    # Add miscellaneous optional variables.
    if 'LD_ENV_OVERRIDES' in make_variables:
        value = make_variables['LD_ENV_OVERRIDES']
        assert value.startswith('env ')
        test_module_variables['LINK_ENVIRONMENT_OVERRIDES'] = value[4:]

    # This isn't possible currently, just here to mark what the option variable
    # would be called.
    if 'COMPILE_ENVIRONMENT_OVERRIDES' in make_variables:
        test_module_variables['COMPILE_ENVIRONMENT_OVERRIDES'] = \
            make_variables['COMPILE_ENVIRONMENT_OVERRIDES']

    if 'EXECUTION_ENVIRONMENT_OVERRIDES' in make_variables:
        test_module_variables['EXECUTION_ENVIRONMENT_OVERRIDES'] = \
            make_variables['EXECUTION_ENVIRONMENT_OVERRIDES']

    # We pass the test execution values as variables too, this might be better
    # passed as actual arguments.
    test_module_variables['THREADS'] = opts.threads
    test_module_variables['BUILD_THREADS'] = opts.build_threads or opts.threads

    return test_module_variables

def execute_nt_tests(test_log, make_variables, basedir, opts):
    common_args = ['make', '-k']
    common_args.extend('%s=%s' % (k,v) for k,v in make_variables.items())
    if opts.only_test is not None:
        common_args.extend(['-C',opts.only_test])

    # Run a separate 'make build' step if --build-threads was given.
    if opts.build_threads > 0:
      args = common_args + ['-j', str(opts.build_threads), 'build']
      print >>test_log, '%s: running: %s' % (timestamp(),
                                             ' '.join('"%s"' % a
                                                      for a in args))
      test_log.flush()

      print >>sys.stderr, '%s: building "nightly tests" with -j%u...' % (
          timestamp(), opts.build_threads)
      p = subprocess.Popen(args=args, stdin=None, stdout=test_log,
                           stderr=subprocess.STDOUT, cwd=basedir,
                           env=os.environ)
      res = p.wait()

    # Then 'make report'.
    args = common_args + ['-j', str(opts.threads),
        'report', 'report.%s.csv' % opts.test_style]
    print >>test_log, '%s: running: %s' % (timestamp(),
                                           ' '.join('"%s"' % a
                                                    for a in args))
    test_log.flush()

    # FIXME: We shouldn't need to set env=os.environ here, but if we don't
    # somehow MACOSX_DEPLOYMENT_TARGET gets injected into the environment on OS
    # X (which changes the driver behavior and causes generally weirdness).
    print >>sys.stderr, '%s: executing "nightly tests" with -j%u...' % (
        timestamp(), opts.threads)
    p = subprocess.Popen(args=args, stdin=None, stdout=test_log,
                         stderr=subprocess.STDOUT, cwd=basedir,
                         env=os.environ)
    res = p.wait()

def load_nt_report_file(report_path, opts):
    # Compute the test samples to report.
    sample_keys = []
    if opts.test_style == "simple":
        test_namespace = 'nts'
        sample_keys.append(('compile', 'CC_Time', None, 'CC'))
        sample_keys.append(('exec', 'Exec_Time', None, 'Exec'))
    else:
        test_namespace = 'nightlytest'
        sample_keys.append(('gcc.compile', 'GCCAS', 'time'))
        sample_keys.append(('bc.compile', 'Bytecode', 'size'))
        if opts.test_llc:
            sample_keys.append(('llc.compile', 'LLC compile', 'time'))
        if opts.test_llcbeta:
            sample_keys.append(('llc-beta.compile', 'LLC-BETA compile', 'time'))
        if opts.test_jit:
            sample_keys.append(('jit.compile', 'JIT codegen', 'time'))
        sample_keys.append(('gcc.exec', 'GCC', 'time'))
        if opts.test_cbe:
            sample_keys.append(('cbe.exec', 'CBE', 'time'))
        if opts.test_llc:
            sample_keys.append(('llc.exec', 'LLC', 'time'))
        if opts.test_llcbeta:
            sample_keys.append(('llc-beta.exec', 'LLC-BETA', 'time'))
        if opts.test_jit:
            sample_keys.append(('jit.exec', 'JIT', 'time'))

    # Load the report file.
    report_file = open(report_path, 'rb')
    reader_it = iter(csv.reader(report_file))

    # Get the header.
    header = reader_it.next()
    if header[0] != 'Program':
        fatal('unexpected report file, missing header')

    # Verify we have the keys we expect.
    if 'Program' not in header:
        fatal('missing key %r in report header' % 'Program')
    for item in sample_keys:
        if item[1] not in header:
            fatal('missing key %r in report header' % item[1])

    # We don't use the test info, currently.
    test_info = {}
    test_samples = []
    for row in reader_it:
        record = dict(zip(header, row))

        program = record['Program']
        if opts.only_test is not None:
            program = os.path.join(opts.only_test, program)
        test_base_name = '%s.%s' % (test_namespace, program.replace('.','_'))

        # Check if this is a subtest result, in which case we ignore missing
        # values.
        if '_Subtest_' in test_base_name:
            is_subtest = True
            test_base_name = test_base_name.replace('_Subtest_', '.')
        else:
            is_subtest = False

        for info in sample_keys:
            if len(info) == 3:
                name,key,tname = info
                success_key = None
            else:
                name,key,tname,success_key = info

            test_name = '%s.%s' % (test_base_name, name)
            value = record[key]
            if success_key is None:
                success_value = value
            else:
                success_value = record[success_key]

            # FIXME: Move to simpler and more succinct format, using .failed.
            if success_value == '*':
                if is_subtest:
                    continue
                status_value = lnt.testing.FAIL
            elif success_value == 'xfail':
                status_value = lnt.testing.XFAIL
            else:
                status_value = lnt.testing.PASS

            if test_namespace == 'nightlytest':
                test_samples.append(lnt.testing.TestSamples(
                        test_name + '.success',
                        [status_value != lnt.testing.FAIL], test_info))
            else:
                if status_value != lnt.testing.PASS:
                    test_samples.append(lnt.testing.TestSamples(
                            test_name + '.status', [status_value], test_info))
            if value != '*':
                if tname is None:
                    test_samples.append(lnt.testing.TestSamples(
                            test_name, [float(value)], test_info))
                else:
                    test_samples.append(lnt.testing.TestSamples(
                            test_name + '.' + tname, [float(value)], test_info))

    report_file.close()

    return test_samples

def compute_run_make_variables(opts, llvm_source_version, target_flags,
                               cc_info):
    # Set the make variables to use.
    make_variables = {
        'TARGET_CC' : opts.cc_reference,
        'TARGET_CXX' : opts.cxx_reference,
        'TARGET_LLVMGCC' : opts.cc_under_test,
        'TARGET_LLVMGXX' : opts.cxx_under_test,
        'TARGET_FLAGS' : ' '.join(target_flags),
        }

    # Compute TARGET_LLCFLAGS, for TEST=nightly runs.
    if opts.test_style == "nightly":
        # Compute TARGET_LLCFLAGS.
        target_llcflags = []
        if opts.mcpu is not None:
            target_llcflags.append('-mcpu')
            target_llcflags.append(opts.mcpu)
        if opts.relocation_model is not None:
            target_llcflags.append('-relocation-model')
            target_llcflags.append(opts.relocation_model)
        if opts.disable_fp_elim:
            target_llcflags.append('-disable-fp-elim')
        make_variables['TARGET_LLCFLAGS'] = ' '.join(target_llcflags)

    # Set up environment overrides if requested, to effectively run under the
    # specified Darwin iOS simulator.
    #
    # See /D/P/../Developer/Tools/RunPlatformUnitTests.
    if opts.ios_simulator_sdk is not None:
        make_variables['EXECUTION_ENVIRONMENT_OVERRIDES'] = ' '.join(
            ['DYLD_FRAMEWORK_PATH="%s"' % opts.ios_simulator_sdk,
             'DYLD_LIBRARY_PATH=""',
             'DYLD_ROOT_PATH="%s"' % opts.ios_simulator_sdk,
             'DYLD_NEW_LOCAL_SHARED_REGIONS=YES',
             'DYLD_NO_FIX_PREBINDING=YES',
             'IPHONE_SIMULATOR_ROOT="%s"' % opts.ios_simulator_sdk,
             'CFFIXED_USER_HOME="%s"' % os.path.expanduser(
                    "~/Library/Application Support/iPhone Simulator/User")])

    # Pick apart the build mode.
    build_mode = opts.build_mode
    if build_mode.startswith("Debug"):
        build_mode = build_mode[len("Debug"):]
        make_variables['ENABLE_OPTIMIZED'] = '0'
    elif build_mode.startswith("Unoptimized"):
        build_mode = build_mode[len("Unoptimized"):]
        make_variables['ENABLE_OPTIMIZED'] = '0'
    elif build_mode.startswith("Release"):
        build_mode = build_mode[len("Release"):]
        make_variables['ENABLE_OPTIMIZED'] = '1'
    else:
        fatal('invalid build mode: %r' % opts.build_mode)

    while build_mode:
        for (name,key) in (('+Asserts', 'ENABLE_ASSERTIONS'),
                           ('+Checks', 'ENABLE_EXPENSIVE_CHECKS'),
                           ('+Coverage', 'ENABLE_COVERAGE'),
                           ('+Debug', 'DEBUG_SYMBOLS'),
                           ('+Profile', 'ENABLE_PROFILING')):
            if build_mode.startswith(name):
                build_mode = build_mode[len(name):]
                make_variables[key] = '1'
                break
        else:
            fatal('invalid build mode: %r' % opts.build_mode)

    # Assertions are disabled by default.
    if 'ENABLE_ASSERTIONS' in make_variables:
        del make_variables['ENABLE_ASSERTIONS']
    else:
        make_variables['DISABLE_ASSERTIONS'] = '1'

    # Set the optimization level options.
    make_variables['OPTFLAGS'] = opts.optimize_option
    if opts.optimize_option == '-Os':
        make_variables['LLI_OPTFLAGS'] = '-O2'
        make_variables['LLC_OPTFLAGS'] = '-O2'
    else:
        make_variables['LLI_OPTFLAGS'] = opts.optimize_option
        make_variables['LLC_OPTFLAGS'] = opts.optimize_option

    # Set test selection variables.
    if not opts.test_cxx:
        make_variables['DISABLE_CXX'] = '1'
    if not opts.test_cbe:
        make_variables['DISABLE_CBE'] = '1'
    if not opts.test_jit:
        make_variables['DISABLE_JIT'] = '1'
    if not opts.test_llc:
        make_variables['DISABLE_LLC'] = '1'
    if not opts.test_lto:
        make_variables['DISABLE_LTO'] = '1'
    if opts.test_llcbeta:
        make_variables['ENABLE_LLCBETA'] = '1'
    if opts.test_small:
        make_variables['SMALL_PROBLEM_SIZE'] = '1'
    if opts.test_integrated_as:
        make_variables['TEST_INTEGRATED_AS'] = '1'
    if opts.liblto_path:
        make_variables['LD_ENV_OVERRIDES'] = (
            'env DYLD_LIBRARY_PATH=%s' % os.path.dirname(
                opts.liblto_path))

    if opts.threads > 1 or opts.build_threads > 1:
        make_variables['ENABLE_PARALLEL_REPORT'] = '1'

    # Select the test style to use.
    if opts.test_style == "simple":
        # We always use reference outputs with TEST=simple.
        make_variables['ENABLE_HASHED_PROGRAM_OUTPUT'] = '1'
        make_variables['USE_REFERENCE_OUTPUT'] = '1'
    make_variables['TEST'] = opts.test_style

    # Set CC_UNDER_TEST_IS_CLANG when appropriate.
    if cc_info.get('cc_name') in ('apple_clang', 'clang'):
        make_variables['CC_UNDER_TEST_IS_CLANG'] = '1'
    elif cc_info.get('cc_name') in ('llvm-gcc',):
        make_variables['CC_UNDER_TEST_IS_LLVM_GCC'] = '1'
    elif cc_info.get('cc_name') in ('gcc',):
        make_variables['CC_UNDER_TEST_IS_GCC'] = '1'

    # Convert the target arch into a make variable, to allow more target based
    # specialization (e.g., CC_UNDER_TEST_TARGET_IS_ARMV7).
    if '-' in cc_info.get('cc_target', ''):
        arch_name = cc_info.get('cc_target').split('-',1)[0]
        make_variables['CC_UNDER_TEST_TARGET_IS_' + arch_name.upper()] = '1'

    # Set LLVM_RELEASE_IS_PLUS_ASSERTS when appropriate, to allow testing older
    # LLVM source trees.
    if (llvm_source_version and llvm_source_version.isdigit() and
        int(llvm_source_version) < 107758):
        make_variables['LLVM_RELEASE_IS_PLUS_ASSERTS'] = 1

    # Set ARCH appropriately, based on the inferred target.
    #
    # FIXME: We should probably be more strict about this.
    cc_target = cc_info.get('cc_target')
    inferred_arch = None
    if cc_target:
        # cc_target is expected to be a (GCC style) target triple. Pick out the
        # arch component, and then try to convert it to an LLVM nightly test
        # style architecture name, which is of course totally different from all
        # of GCC names, triple names, LLVM target names, and LLVM triple
        # names. Stupid world.
        #
        # FIXME: Clean this up once everyone is on 'lnt runtest nt' style
        # nightly testing.
        arch = cc_target.split('-',1)[0].lower()
        if (len(arch) == 4 and arch[0] == 'i' and arch.endswith('86') and
            arch[1] in '3456789'): # i[3-9]86
            inferred_arch = 'x86'
        elif arch in ('x86_64', 'amd64'):
            inferred_arch = 'x86_64'
        elif arch in ('powerpc', 'powerpc64', 'ppu'):
            inferred_arch = 'PowerPC'
        elif (arch == 'arm' or arch.startswith('armv') or
              arch == 'thumb' or arch.startswith('thumbv') or
              arch == 'xscale'):
            inferred_arch = 'ARM'
        elif arch.startswith('alpha'):
            inferred_arch = 'Alpha'
        elif arch.startswith('sparc'):
            inferred_arch = 'Sparc'

    if inferred_arch:
        make_variables['ARCH'] = inferred_arch
    else:
        warning("unable to infer ARCH, some tests may not run correctly!")

    return make_variables

def run_test(nick_prefix, opts, iteration):
    print >>sys.stderr, "%s: checking source versions" % (
        timestamp(),)
    if opts.llvm_src_root:
        llvm_source_version = get_source_version(opts.llvm_src_root)
    else:
        llvm_source_version = None
    test_suite_source_version = get_source_version(opts.test_suite_root)

    # Compute TARGET_FLAGS.
    target_flags = []

    # FIXME: Eliminate this blanket option.
    target_flags.extend(opts.cflags)

    # Pass flags to backend.
    for f in opts.mllvm:
      target_flags.extend(['-mllvm', f])

    if opts.arch is not None:
        target_flags.append('-arch')
        target_flags.append(opts.arch)
    if opts.isysroot is not None:
        target_flags.append('-isysroot')
        target_flags.append(opts.isysroot)

    # Get compiler info.
    cc_info = lnt.testing.util.compilers.get_cc_info(opts.cc_under_test,
                                                     target_flags)
    cc_target = cc_info.get('cc_target')

    # Compute the make variables.
    make_variables = compute_run_make_variables(opts, llvm_source_version,
                                                target_flags, cc_info)

    # Stash the variables we want to report.
    public_make_variables = make_variables.copy()

    # Set remote execution variables, if used.
    if opts.remote:
        make_variables['REMOTE_HOST'] = opts.remote_host
        make_variables['REMOTE_USER'] = opts.remote_user
        make_variables['REMOTE_PORT'] = str(opts.remote_port)
        make_variables['REMOTE_CLIENT'] = opts.remote_client

    # Compute the test module variables, which are a restricted subset of the
    # make variables.
    test_module_variables = compute_test_module_variables(make_variables, opts)

    # Scan for LNT-based test modules.
    print >>sys.stderr, "%s: scanning for LNT-based test modules" % (
        timestamp(),)
    test_modules = list(scan_for_test_modules(opts))
    print >>sys.stderr, "%s: found %d LNT-based test modules" % (
        timestamp(), len(test_modules))

    nick = nick_prefix
    if opts.auto_name:
        # Construct the nickname from a few key parameters.
        cc_nick = '%s_%s' % (cc_info.get('cc_name'), cc_info.get('cc_build'))
        nick += "__%s__%s" % (cc_nick, cc_info.get('cc_target').split('-')[0])
    print >>sys.stderr, "%s: using nickname: %r" % (timestamp(), nick)

    # Set up the sandbox.
    if not os.path.exists(opts.sandbox_path):
        print >>sys.stderr, "%s: creating sandbox: %r" % (
            timestamp(), opts.sandbox_path)
        os.mkdir(opts.sandbox_path)

    # Create the per-test directory.
    start_time = timestamp()
    if opts.timestamp_build:
        ts = start_time.replace(' ','_').replace(':','-')
        build_dir_name = "test-%s" % ts
    else:
        build_dir_name = "build"
    if iteration is not None:
        build_dir_name = "%s-%d" % (build_dir_name, iteration)
    basedir = os.path.join(opts.sandbox_path, build_dir_name)

    # Canonicalize paths, in case we are using e.g. an NFS remote mount.
    #
    # FIXME: This should be eliminated, along with the realpath call below.
    basedir = os.path.realpath(basedir)

    if os.path.exists(basedir):
        needs_clean = True
    else:
        needs_clean = False
        os.mkdir(basedir)

    # Unless not using timestamps, we require the basedir not to exist.
    if needs_clean and opts.timestamp_build:
        fatal('refusing to reuse pre-existing build dir %r' % basedir)

    # FIXME: Auto-remove old test directories in the source directory (which
    # cause make horrible fits).

    print >>sys.stderr, '%s: starting test in %r' % (timestamp(), basedir)

    # Configure the test suite.
    if opts.run_configure or not os.path.exists(os.path.join(
            basedir, 'Makefile.config')):
        configure_log_path = os.path.join(basedir, 'configure.log')
        configure_log = open(configure_log_path, 'w')

        args = [os.path.realpath(os.path.join(opts.test_suite_root,
                                              'configure'))]
        if opts.without_llvm:
            args.extend(['--without-llvmsrc', '--without-llvmobj'])
        else:
            args.extend(['--with-llvmsrc=%s' % opts.llvm_src_root,
                         '--with-llvmobj=%s' % opts.llvm_obj_root])
        args.append('--with-externals=%s' % os.path.realpath(
                opts.test_suite_externals))
        print >>configure_log, '%s: running: %s' % (timestamp(),
                                                    ' '.join('"%s"' % a
                                                             for a in args))
        configure_log.flush()

        print >>sys.stderr, '%s: configuring...' % timestamp()
        p = subprocess.Popen(args=args, stdin=None, stdout=configure_log,
                             stderr=subprocess.STDOUT, cwd=basedir)
        res = p.wait()
        configure_log.close()
        if res != 0:
            fatal('configure failed, log is here: %r' % configure_log_path)

    # If running with --only-test, creating any dirs which might be missing and
    # copy Makefiles.
    if opts.only_test is not None and not opts.only_test.startswith("LNTBased"):
        suffix = ''
        for component in opts.only_test.split('/'):
            suffix = os.path.join(suffix, component)
            obj_path = os.path.join(basedir, suffix)
            src_path = os.path.join(opts.test_suite_root, suffix)
            if not os.path.exists(obj_path):
                print '%s: initializing test dir %s' % (timestamp(), suffix)
                os.mkdir(obj_path)
                shutil.copyfile(os.path.join(src_path, 'Makefile'),
                                os.path.join(obj_path, 'Makefile'))

    # If running without LLVM, make sure tools are up to date.
    if opts.without_llvm:
        print >>sys.stderr, '%s: building test-suite tools' % (timestamp(),)
        args = ['make', 'tools']
        args.extend('%s=%s' % (k,v) for k,v in make_variables.items())
        build_tools_log_path = os.path.join(basedir, 'build-tools.log')
        build_tools_log = open(build_tools_log_path, 'w')
        print >>build_tools_log, '%s: running: %s' % (timestamp(),
                                                      ' '.join('"%s"' % a
                                                               for a in args))
        build_tools_log.flush()
        p = subprocess.Popen(args=args, stdin=None, stdout=build_tools_log,
                             stderr=subprocess.STDOUT, cwd=basedir,
                             env=os.environ)
        res = p.wait()
        build_tools_log.close()
        if res != 0:
            fatal('unable to build tools, aborting!')
        
    # Always blow away any existing report.
    report_path = os.path.join(basedir)
    if opts.only_test is not None:
        report_path =  os.path.join(report_path, opts.only_test)
    report_path = os.path.join(report_path, 'report.%s.csv' % opts.test_style)
    if os.path.exists(report_path):
        os.remove(report_path)

    # Execute the tests.
    test_log_path = os.path.join(basedir, 'test.log')
    test_log = open(test_log_path, 'w')

    # Run the make driven tests if needed.
    run_nightly_test = (opts.only_test is None or
                        not opts.only_test.startswith("LNTBased"))
    if run_nightly_test:
        execute_nt_tests(test_log, make_variables, basedir, opts)

    # Run the extension test modules, if needed.
    test_module_results = execute_test_modules(test_log, test_modules,
                                               test_module_variables, basedir,
                                               opts)

    test_log.close()

    end_time = timestamp()

    # Load the nightly test samples.
    if opts.test_style == "simple":
        test_namespace = 'nts'
    else:
        test_namespace = 'nightlytest'
    if run_nightly_test:
        print >>sys.stderr, '%s: loading nightly test data...' % timestamp()
        # If nightly test went screwy, it won't have produced a report.
        if not os.path.exists(report_path):
            fatal('nightly test failed, no report generated')

        test_samples = load_nt_report_file(report_path, opts)
    else:
        test_samples = []

    # Merge in the test samples from all of the test modules.
    existing_tests = set(s.name for s in test_samples)
    for module,results in test_module_results:
        for s in results:
            if s.name in existing_tests:
                fatal("test module %r added duplicate test: %r" % (
                        module, s.name))
            existing_tests.add(s.name)
        test_samples.extend(results)

    print >>sys.stderr, '%s: capturing machine information' % (timestamp(),)
    # Collect the machine and run info.
    #
    # FIXME: Import full range of data that the Clang tests are using?
    machine_info = {}
    machine_info['hardware'] = capture(["uname","-m"],
                                       include_stderr=True).strip()
    machine_info['os'] = capture(["uname","-sr"], include_stderr=True).strip()
    if opts.cc_reference is not None:
        machine_info['gcc_version'] = capture(
            [opts.cc_reference, '--version'],
            include_stderr=True).split('\n')[0]

    # FIXME: We aren't getting the LLCBETA options.
    run_info = {}
    run_info['tag'] = test_namespace
    run_info.update(cc_info)

    # Capture sw_vers if this looks like Darwin.
    if 'Darwin' in machine_info['os']:
        run_info['sw_vers'] = capture(['sw_vers'], include_stderr=True).strip()

    # Query remote properties if in use.
    if opts.remote:
        remote_args = [opts.remote_client,
                       "-l", opts.remote_user,
                       "-p",  str(opts.remote_port),
                       opts.remote_host]
        run_info['remote_uname'] = capture(remote_args + ["uname", "-a"],
                                           include_stderr=True).strip()

        # Capture sw_vers if this looks like Darwin.
        if 'Darwin' in run_info['remote_uname']:
            run_info['remote_sw_vers'] = capture(remote_args + ["sw_vers"],
                                                 include_stderr=True).strip()

    # Add machine dependent info.
    if opts.use_machdep_info:
        machdep_info = machine_info
    else:
        machdep_info = run_info

    machdep_info['uname'] = capture(["uname","-a"], include_stderr=True).strip()
    machdep_info['name'] = capture(["uname","-n"], include_stderr=True).strip()

    # FIXME: Hack, use better method of getting versions. Ideally, from binaries
    # so we are more likely to be accurate.
    if llvm_source_version is not None:
        run_info['llvm_revision'] = llvm_source_version
    run_info['test_suite_revision'] = test_suite_source_version
    run_info.update(public_make_variables)

    # Set the run order from the user, if given.
    if opts.run_order is not None:
        run_info['run_order'] = opts.run_order

    else:
        # Otherwise, try to infer something sensible.
        #
        # FIXME: Pretty lame, should we just require the user to specify this?

        # If the CC has a src revision, use that.
        if run_info.get('cc_src_revision','').isdigit():
            run_info['run_order'] = run_info['cc_src_revision']

        # Otherwise, if this is a production compiler, look for a source tag. We
        # don't accept 0 or 9999 as valid source tag, since that is what
        # llvm-gcc builds use when no build number is given.
        elif (run_info.get('cc_build') == 'PROD' and
              run_info.get('cc_src_tag') != '0' and
              run_info.get('cc_src_tag') != '00' and
              run_info.get('cc_src_tag') != '9999' and
              run_info.get('cc_src_tag','').split('.',1)[0].isdigit()):
            run_info['run_order'] = run_info['cc_src_tag'].split('.',1)[0]

        # Otherwise, infer from the llvm revision.
        elif run_info.get('llvm_revision','').isdigit():
            run_info['run_order'] = run_info['llvm_revision']

        # Otherwise, force at least some value for run_order, as it is now
        # generally required by parts of the "simple" schema.
        else:
            run_info['run_order'] = "0"

        if 'run_order' in run_info:
            run_info['run_order'] = '%7d' % int(run_info['run_order'])

    # Add any user specified parameters.
    for target,params in ((machine_info, opts.machine_parameters),
                          (run_info, opts.run_parameters)):
        for entry in params:
            if '=' not in entry:
                name,value = entry,''
            else:
                name,value = entry.split('=', 1)
            if name in target:
                warning("user parameter %r overwrote existing value: %r" % (
                        name, target.get(name)))
            print target,name,value
            target[name] = value

    # Generate the test report.
    lnt_report_path = os.path.join(basedir, 'report.json')
    print >>sys.stderr, '%s: generating report: %r' % (timestamp(),
                                                       lnt_report_path)
    machine = lnt.testing.Machine(nick, machine_info)
    run = lnt.testing.Run(start_time, end_time, info = run_info)

    report = lnt.testing.Report(machine, run, test_samples)
    lnt_report_file = open(lnt_report_path, 'w')
    print >>lnt_report_file,report.render()
    lnt_report_file.close()

    return report, basedir

###

import builtintest
from optparse import OptionParser, OptionGroup

usage_info = """
Script for running the tests in LLVM's test-suite repository.

This script expects to run against a particular LLVM source tree, build, and
compiler. It is only responsible for running the tests in the test-suite
repository, and formatting the results for submission to an LNT server.

Basic usage:

  %%prog %(name)s \\
    --sandbox FOO \\
    --cc ~/llvm.obj.64/Release/bin/clang \\
    --cxx ~/llvm.obj.64/Release/bin/clang++ \\
    --test-suite ~/llvm-test-suite \\
    FOO

where --sandbox is the directory to build and store results in, --cc and --cxx
are the full paths to the compilers to test, and --test-suite is the path to the
test-suite source. The final argument is the base nickname to use to describe
this run in reports.

To do a quick test, you can add something like:

    -j 16 --only-test SingleSource

which will run with 16 threads and only run the tests inside SingleSource.

To do a really quick test, you can further add

    --no-timestamp --no-configure

which will cause the same build directory to be used, and the configure step
will be skipped if it appears to already have been configured. This is
effectively an incremental retest. It is useful for testing the scripts or
nightly test, but it should not be used for submissions."""

class NTTest(builtintest.BuiltinTest):
    def describe(self):
        return 'LLVM test-suite compile and execution tests'

    def run_test(self, name, args):
        parser = OptionParser(
            ("%%prog %(name)s [options] tester-name\n" + usage_info) % locals())

        group = OptionGroup(parser, "Sandbox Options")
        group.add_option("-s", "--sandbox", dest="sandbox_path",
                         help="Parent directory to build and run tests in",
                         type=str, default=None, metavar="PATH")
        group.add_option("", "--no-timestamp", dest="timestamp_build",
                         help="Don't timestamp build directory (for testing)",
                         action="store_false", default=True)
        group.add_option("", "--no-configure", dest="run_configure",
                         help=("Don't run configure if Makefile.config is "
                               "present (only useful with --no-timestamp)"),
                         action="store_false", default=True)
        parser.add_option_group(group)

        group = OptionGroup(parser, "Inputs")
        group.add_option("", "--without-llvm", dest="without_llvm",
                         help="Don't use any LLVM source or build products",
                         action="store_true", default=False)
        group.add_option("", "--llvm-src", dest="llvm_src_root",
                         help="Path to the LLVM source tree",
                         type=str, default=None, metavar="PATH")
        group.add_option("", "--llvm-obj", dest="llvm_obj_root",
                         help="Path to the LLVM source tree",
                         type=str, default=None, metavar="PATH")
        group.add_option("", "--test-suite", dest="test_suite_root",
                         help="Path to the LLVM test-suite sources",
                         type=str, default=None, metavar="PATH")
        group.add_option("", "--test-externals", dest="test_suite_externals",
                         help="Path to the LLVM test-suite externals",
                         type=str, default='/dev/null', metavar="PATH")
        parser.add_option_group(group)

        group = OptionGroup(parser, "Test Compiler")
        group.add_option("", "--cc", dest="cc_under_test", metavar="CC",
                         help="Path to the C compiler to test",
                         type=str, default=None)
        group.add_option("", "--cxx", dest="cxx_under_test", metavar="CXX",
                         help="Path to the C++ compiler to test",
                         type=str, default=None)
        group.add_option("", "--cc-reference", dest="cc_reference",
                         help="Path to the reference C compiler",
                         type=str, default=None)
        group.add_option("", "--cxx-reference", dest="cxx_reference",
                         help="Path to the reference C++ compiler",
                         type=str, default=None)
        parser.add_option_group(group)

        group = OptionGroup(parser, "Test Options")
        group.add_option("", "--arch", dest="arch",
                         help="Set -arch in TARGET_FLAGS [%default]",
                         type=str, default=None)
        group.add_option("", "--isysroot", dest="isysroot", metavar="PATH",
                         help="Set -isysroot in TARGET_FLAGS [%default]",
                         type=str, default=None)
        group.add_option("", "--liblto-path", dest="liblto_path",
                         metavar="PATH",
                         help=("Specify the path to the libLTO library "
                               "[%default]"),
                         type=str, default=None)

        group.add_option("", "--mcpu", dest="mcpu",
                         help="Set -mcpu in TARGET_LLCFLAGS [%default]",
                         type=str, default=None, metavar="CPU")
        group.add_option("", "--relocation-model", dest="relocation_model",
                         help=("Set -relocation-model in TARGET_LLCFLAGS "
                                "[%default]"),
                         type=str, default=None, metavar="MODEL")
        group.add_option("", "--disable-fp-elim", dest="disable_fp_elim",
                         help=("Set -disable-fp-elim in TARGET_LLCFLAGS"),
                         action="store_true", default=False)

        group.add_option("", "--optimize-option", dest="optimize_option",
                         help="Set optimization level for {LLC_,LLI_,}OPTFLAGS",
                         choices=('-O0','-O1','-O2','-O3','-Os'), default='-O3')
        group.add_option("", "--cflag", dest="cflags",
                         help="Additional flags to set in TARGET_FLAGS",
                         action="append", type=str, default=[], metavar="FLAG")
        group.add_option("", "--mllvm", dest="mllvm",
                         help="Add -mllvm FLAG to TARGET_FLAGS",
                         action="append", type=str, default=[], metavar="FLAG")
        parser.add_option_group(group)

        group = OptionGroup(parser, "Test Selection")
        group.add_option("", "--build-mode", dest="build_mode", metavar="NAME",
                         help="Select the LLVM build mode to use [%default]",
                         type=str, action="store", default='Release+Asserts')

        group.add_option("", "--simple", dest="test_simple",
                         help="Use TEST=simple instead of TEST=nightly",
                         action="store_true", default=False)
        group.add_option("", "--test-style", dest="test_style",
                         help="Set the test style to run [%default]",
                         choices=('nightly', 'simple'), default='simple')

        group.add_option("", "--disable-cxx", dest="test_cxx",
                         help="Disable C++ tests",
                         action="store_false", default=True)

        group.add_option("", "--enable-cbe", dest="test_cbe",
                         help="Enable CBE tests",
                         action="store_true", default=False)
        group.add_option("", "--disable-externals", dest="test_externals",
                         help="Disable test suite externals (if configured)",
                         action="store_false", default=True)
        group.add_option("", "--enable-integrated-as",dest="test_integrated_as",
                         help="Enable TEST_INTEGRATED_AS tests",
                         action="store_true", default=False)
        group.add_option("", "--enable-jit", dest="test_jit",
                         help="Enable JIT tests",
                         action="store_true", default=False)
        group.add_option("", "--disable-llc", dest="test_llc",
                         help="Disable LLC tests",
                         action="store_false", default=True)
        group.add_option("", "--enable-llcbeta", dest="test_llcbeta",
                         help="Enable LLCBETA tests",
                         action="store_true", default=False)
        group.add_option("", "--disable-lto", dest="test_lto",
                         help="Disable use of link-time optimization",
                         action="store_false", default=True)

        group.add_option("", "--small", dest="test_small",
                         help="Use smaller test inputs and disable large tests",
                         action="store_true", default=False)

        group.add_option("", "--only-test", dest="only_test", metavar="PATH",
                         help="Only run tests under PATH",
                         type=str, default=None)
        group.add_option("", "--include-test-examples",
                         dest="include_test_examples",
                         help="Include test module examples [%default]",
                         action="store_true", default=False)
        parser.add_option_group(group)

        group = OptionGroup(parser, "Test Execution")
        group.add_option("-j", "--threads", dest="threads",
                         help="Number of testing threads",
                         type=int, default=1, metavar="N")
        group.add_option("", "--build-threads", dest="build_threads",
                         help="Number of compilation threads",
                         type=int, default=0, metavar="N")

        group.add_option("", "--remote", dest="remote",
                         help=("Execute remotely, see "
                               "--remote-{host,port,user,client} [%default]"),
                         action="store_true", default=False)
        group.add_option("", "--remote-host", dest="remote_host",
                         help="Set remote execution host [%default]",
                         type=str, default="localhost", metavar="HOST")
        group.add_option("", "--remote-port", dest="remote_port",
                         help="Set remote execution port [%default] ",
                         type=int, default=None, metavar="PORT",)
        group.add_option("", "--remote-user", dest="remote_user",
                         help="Set remote execution user [%default]",
                         type=str, default=None, metavar="USER",)
        group.add_option("", "--remote-client", dest="remote_client",
                         help="Set remote execution client [%default]",
                         type=str, default="ssh", metavar="RSH",)

        group.add_option("", "--use-ios-simulator", dest="ios_simulator_sdk",
                         help=("Execute using an iOS simulator SDK (using "
                               "environment overrides)"),
                         type=str, default=None, metavar="SDKPATH")

        group.add_option("", "--multisample", dest="multisample",
                         help="Accumulate test data from multiple runs",
                         type=int, default=None, metavar="N")
        parser.add_option_group(group)

        group = OptionGroup(parser, "Output Options")
        group.add_option("", "--no-auto-name", dest="auto_name",
                         help="Don't automatically derive submission name",
                         action="store_false", default=True)
        group.add_option("", "--no-machdep-info", dest="use_machdep_info",
                         help=("Don't put machine (instance) dependent "
                               "variables with machine info"),
                         action="store_false", default=True)
        group.add_option("", "--run-order", dest="run_order", metavar="STR",
                          help="String to use to identify and order this run",
                          action="store", type=str, default=None)
        group.add_option("", "--machine-param", dest="machine_parameters",
                         metavar="NAME=VAL",
                         help="Add 'NAME' = 'VAL' to the machine parameters",
                         type=str, action="append", default=[])
        group.add_option("", "--run-param", dest="run_parameters",
                         metavar="NAME=VAL",
                         help="Add 'NAME' = 'VAL' to the run parameters",
                         type=str, action="append", default=[])
        parser.add_option_group(group)

        (opts, args) = parser.parse_args(args)
        if len(args) != 1:
            parser.error("invalid number of arguments")

        nick, = args

        # The --without--llvm option is the default if no LLVM paths are given.
        if opts.llvm_src_root is None and opts.llvm_obj_root is None:
            opts.without_llvm = True

        # Validate options.

        if opts.sandbox_path is None:
            parser.error('--sandbox is required')

        # Deprecate --simple.
        if opts.test_simple:
            warning("--simple is deprecated, it is the default.")
        del opts.test_simple

        if opts.test_style == "simple":
            # TEST=simple doesn't use a reference compiler.
            if opts.cc_reference is not None:
                parser.error('--cc-reference is unused with --simple')
            if opts.cxx_reference is not None:
                parser.error('--cxx-reference is unused with --simple')
            # TEST=simple doesn't use a llc options.
            if opts.mcpu is not None:
                parser.error('--mcpu is unused with --simple (use --cflag)')
            if opts.relocation_model is not None:
                parser.error('--relocation-model is unused with --simple '
                             '(use --cflag)')
            if opts.disable_fp_elim:
                parser.error('--disable-fp-elim is unused with --simple '
                             '(use --cflag)')
        else:
            if opts.without_llvm:
                parser.error('--simple is required with --without-llvm')

            # Attempt to infer cc_reference and cxx_reference if not given.
            if opts.cc_reference is None:
                opts.cc_reference = which('gcc') or which('cc')
                if opts.cc_reference is None:
                    parser.error('unable to infer --cc-reference (required)')
            if opts.cxx_reference is None:
                opts.cxx_reference = which('g++') or which('c++')
                if opts.cxx_reference is None:
                    parser.error('unable to infer --cxx-reference (required)')

        if opts.cc_under_test is None:
            parser.error('--cc is required')
        if opts.test_cxx and opts.cxx_under_test is None:
            parser.error('--cxx is required')

        # Always set cxx_under_test, since it may be used as the linker even
        # when not testing C++ code.
        if opts.cxx_under_test is None:
            opts.cxx_under_test = opts.cc_under_test

        # FIXME: As a hack to allow sampling old Clang revisions, if we are
        # given a C++ compiler that doesn't exist, reset it to just use the
        # given C compiler.
        if not os.path.exists(opts.cxx_under_test):
            warning("invalid cxx_under_test, falling back to cc_under_test")
            opts.cxx_under_test = opts.cc_under_test

        if opts.without_llvm:
            if opts.llvm_src_root is not None:
                parser.error('--llvm-src is not allowed with --without-llvm')
            if opts.llvm_obj_root is not None:
                parser.error('--llvm-obj is not allowed with --without-llvm')
        else:
            if opts.llvm_src_root is None:
                parser.error('--llvm-src is required')
            if opts.llvm_obj_root is None:
                parser.error('--llvm-obj is required')

            # Make LLVM source and object paths absolute, this is required.
            opts.llvm_src_root = os.path.abspath(opts.llvm_src_root)
            opts.llvm_obj_root = os.path.abspath(opts.llvm_obj_root)
            if not os.path.exists(opts.llvm_src_root):
                parser.error('--llvm-src argument does not exist')
            if not os.path.exists(opts.llvm_obj_root):
                parser.error('--llvm-obj argument does not exist')

        if opts.test_suite_root is None:
            parser.error('--test-suite is required')
        elif not os.path.exists(opts.test_suite_root):
            parser.error("invalid --test-suite argument, does not exist: %r" % (
                    opts.test_suite_root))
            
        if opts.remote:
            if opts.remote_port is None:
                parser.error('--remote-port is required with --remote')
            if opts.remote_user is None:
                parser.error('--remote-user is required with --remote')

        # libLTO should exist, if given.
        if opts.liblto_path:
            if not os.path.exists(opts.liblto_path):
                parser.error('invalid --liblto-path argument %r' % (
                        opts.liblto_path,))

        # Support disabling test suite externals separately from providing path.
        if not opts.test_externals:
            opts.test_suite_externals = '/dev/null'

        # Set up iOS simulator options.
        if opts.ios_simulator_sdk:
            # Warn if the user asked to run under an iOS simulator SDK, but
            # didn't set an isysroot for compilation.
            if opts.isysroot is None:
                warning('expected --isysroot when executing with '
                        '--ios-simulator-sdk')

        # FIXME: We need to validate that there is no configured output in the
        # test-suite directory, that borks things. <rdar://problem/7876418>

        # Multisample, if requested.
        if opts.multisample is not None:
            # Collect the sample reports.
            reports = []
            first_basedir = None
            for i in range(opts.multisample):
                print >>sys.stderr, "%s: (multisample) running iteration %d" % (
                    timestamp(), i)
                report, basedir = run_test(nick, opts, i)
                reports.append(report)
                if first_basedir is None:
                    first_basedir = basedir

            # Create the merged report.
            #
            # FIXME: Do a more robust job of merging the reports?
            print >>sys.stderr, "%s: (multisample) creating merged report" % (
                timestamp(),)
            machine = reports[0].machine
            run = reports[0].run
            run.end_time = reports[-1].run.end_time
            test_samples = sum([r.tests
                                for r in reports], [])

            # Write out the merged report.
            lnt_report_path = os.path.join(first_basedir, 'report-merged.json')
            report = lnt.testing.Report(machine, run, test_samples)
            lnt_report_file = open(lnt_report_path, 'w')
            print >>lnt_report_file,report.render()
            lnt_report_file.close()

            return report

        report, _ = run_test(nick, opts, None)
        return report

def create_instance():
    return NTTest()

__all__ = ['create_instance']
