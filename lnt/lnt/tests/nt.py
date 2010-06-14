import csv
import os
import re
import subprocess
import sys
import time

from datetime import datetime

import lnt.testing
import lnt.testing.util.compilers

from lnt.testing.util.commands import note, warning, error, fatal
from lnt.testing.util.commands import capture, which
from lnt.testing.util.rcs import get_source_version

def timestamp():
    return datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

def run_test(nick_prefix, opts):
    # Compute TARGET_FLAGS.
    target_flags = []

    # FIXME: Eliminate this blanket option.
    target_flags.extend(opts.cflags)

    if opts.arch is not None:
        target_flags.append('-arch')
        target_flags.append(opts.arch)
    if opts.isysroot is not None:
        target_flags.append('-isysroot')
        target_flags.append(opts.isysroot)

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

    # Set the make variables to use.
    make_variables = {
        'TARGET_CC' : opts.cc_reference,
        'TARGET_LLVMGCC' : opts.cc_under_test,
        'TARGET_FLAGS' : ' '.join(target_flags),
        'TARGET_LLCFLAGS' : ' '.join(target_llcflags),
        'ENABLE_OPTIMIZED' : '1',
        }

    # Set the optimization level options.
    make_variables['OPTFLAGS'] = opts.optimize_option
    if opts.optimize_option == '-Os':
        make_variables['LLI_OPTFLAGS'] = '-O2'
        make_variables['LLC_OPTFLAGS'] = '-O2'
    else:
        make_variables['LLI_OPTFLAGS'] = opts.optimize_option
        make_variables['LLC_OPTFLAGS'] = opts.optimize_option

    # Set test selection variables.
    make_variables['TARGET_CXX'] = opts.cxx_reference
    if opts.test_cxx:
        make_variables['TARGET_LLVMGXX'] = opts.cxx_under_test
    else:
        make_variables['TARGET_LLVMGXX'] = 'false'
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

    if opts.threads > 1:
        make_variables['ENABLE_PARALLEL_REPORT'] = '1'

    # Select the test style to use.
    if opts.test_simple:
        test_style = 'simple'
        # We always use reference outputs with TEST=simple.
        make_variables['ENABLE_HASHED_PROGRAM_OUTPUT'] = '1'
        make_variables['USE_REFERENCE_OUTPUT'] = '1'
    else:
        test_style = 'nightly'
    make_variables['TEST'] = test_style

    # Support disabling test suite externals separately from providing path.
    if not opts.test_externals:
        opts.test_suite_externals = '/dev/null'

    # Get compiler info.
    cc_info = lnt.testing.util.compilers.get_cc_info(opts.cc_under_test,
                                                     target_flags)

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

    # Stash the variables we want to report.
    public_make_variables = make_variables.copy()

    # Set remote execution variables, if used.
    if opts.remote:
        make_variables['REMOTE_HOST'] = opts.remote_host
        make_variables['REMOTE_USER'] = opts.remote_user
        make_variables['REMOTE_PORT'] = str(opts.remote_port)
        make_variables['REMOTE_CLIENT'] = opts.remote_client

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

    # FIXME: Auto-remove old test directories.

    print >>sys.stderr, '%s: starting test in %r' % (timestamp(), basedir)

    # Configure the test suite.
    if opts.run_configure or not os.path.exists(os.path.join(
            basedir, 'Makefile.config')):
        configure_log_path = os.path.join(basedir, 'configure.log')
        configure_log = open(configure_log_path, 'w')

        args = [os.path.realpath(os.path.join(opts.test_suite_root,
                                              'configure')),
                '--with-llvmsrc=%s' % opts.llvm_src_root,
                '--with-llvmobj=%s' % opts.llvm_obj_root,
                '--with-externals=%s' % opts.test_suite_externals]
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

    # Always blow away any existing report.
    report_path = os.path.join(basedir)
    if opts.only_test is not None:
        report_path =  os.path.join(report_path, opts.only_test)
    report_path = os.path.join(report_path, 'report.%s.csv' % test_style)
    if os.path.exists(report_path):
        os.remove(report_path)

    # Execute the tests.
    test_log_path = os.path.join(basedir, 'test.log')
    test_log = open(test_log_path, 'w')

    args = ['make', '-k', '-j', str(opts.threads),
            'report', 'report.%s.csv' % test_style]
    args.extend('%s=%s' % (k,v) for k,v in make_variables.items())
    if opts.only_test is not None:
        args.extend(['-C',opts.only_test])
    print >>test_log, '%s: running: %s' % (timestamp(),
                                           ' '.join('"%s"' % a
                                                    for a in args))
    test_log.flush()

    # FIXME: We shouldn't need to set env=os.environ here, but if we don't
    # somehow MACOSX_DEPLOYMENT_TARGET gets injected into the environment on OS
    # X (which changes the driver behavior and causes generally weirdness).
    print >>sys.stderr, '%s: testing...' % timestamp()
    p = subprocess.Popen(args=args, stdin=None, stdout=test_log,
                         stderr=subprocess.STDOUT, cwd=basedir,
                         env=os.environ)
    res = p.wait()
    test_log.close()

    end_time = timestamp()

    # Compute the test samples to report.
    sample_keys = []
    if opts.test_simple:
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

    # Load the test samples.
    print >>sys.stderr, '%s: loading test data...' % timestamp()
    test_samples = []

    # If nightly test went screwy, it won't have produced a report.
    if not os.path.exists(report_path):
        fatal('nightly test failed, no report generated')

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
    for row in reader_it:
        record = dict(zip(header, row))

        program = record['Program']
        if opts.only_test is not None:
            program = os.path.join(opts.only_test, program)
        test_base_name = '%s.%s' % (test_namespace, program.replace('.','_'))
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

    # Collect the machine and run info.
    #
    # FIXME: Support no-machdep-info.
    #
    # FIXME: Import full range of data that the Clang tests are using?
    machine_info = {}
    machine_info['uname'] = capture(["uname","-a"],
                                    include_stderr=True).strip()
    machine_info['hardware'] = capture(["uname","-m"],
                                       include_stderr=True).strip()
    machine_info['os'] = capture(["uname","-sr"], include_stderr=True).strip()
    machine_info['name'] = capture(["uname","-n"], include_stderr=True).strip()
    if opts.cc_reference is not None:
        machine_info['gcc_version'] = capture(
            [opts.cc_reference, '--version'],
            include_stderr=True).split('\n')[0]
    machine = lnt.testing.Machine(nick, machine_info)

    # FIXME: We aren't getting the LLCBETA options.
    run_info = {}
    run_info['tag'] = test_namespace
    run_info.update(cc_info)

    # FIXME: Hack, use better method of getting versions. Ideally, from binaries
    # so we are more likely to be accurate.
    run_info['llvm_revision'] = get_source_version(opts.llvm_src_root)
    run_info['test_suite_revision'] = get_source_version(opts.test_suite_root)
    run_info.update(public_make_variables)

    # Set the run order from the user, if given.
    if opts.run_order is not None:
        run_info['run_order'] = opts.run_order

    else:
        # Otherwise, try to infer something sensible.
        #
        # FIXME: Pretty lame, should we just require the user to specify this?

        # If the CC has a src revision, use that.
        if run_info.get('cc_src_version','').isdigit():
            run_info['run_order'] = run_info['cc_src_revision']

        # Otherwise, if this is a production compiler, look for a source tag.
        elif (run_info.get('cc_build') == 'PROD' and
              run_info.get('cc_src_tag','').isdigit()):
            run_info['run_order'] = run_info['cc_src_tag']

        # Otherwise, infer from the llvm revision.
        elif run_info.get('llvm_revision','').isdigit():
            run_info['run_order'] = run_info['llvm_revision']

        if 'run_order' in run_info:
            run_info['run_order'] = '%7d' % int(run_info['run_order'])

    # Generate the test report.
    lnt_report_path = os.path.join(basedir, 'report.json')
    print >>sys.stderr, '%s: generating report: %r' % (timestamp(),
                                                       lnt_report_path)
    run = lnt.testing.Run(start_time, end_time, info = run_info)

    report = lnt.testing.Report(machine, run, test_samples)
    lnt_report_file = open(lnt_report_path, 'w')
    print >>lnt_report_file,report.render()
    lnt_report_file.close()

    return report

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
    --llvm-src ~/llvm \\
    --llvm-obj ~/llvm.obj.64 \\
    --test-suite ~/llvm-test-suite \\
    FOO

where --sandbox is the directory to build and store results in, --cc and --cxx
are the full paths to the compilers to test, and the remaining options are paths
to the LLVM source tree, LLVM object tree, and test-suite source tree. The final
argument is the base nickname to use to describe this run in reports.

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

        group.add_option("", "--mcpu", dest="mcpu",
                         help="Set -mcpu in TARGET_LLCFLAGS [%default]",
                         type=str, default=None, metavar="CPU")
        group.add_option("", "--relocation-model", dest="relocation_model",
                         help=("Set -relocation-model in TARGET_LLCFLAGS "
                                "[%default]"),
                         type="str", default=None, metavar="MODEL")
        group.add_option("", "--disable-fp-elim", dest="disable_fp_elim",
                         help=("Set -disable-fp-elim in TARGET_LLCFLAGS"),
                         action="store_true", default=False)

        group.add_option("", "--optimize-option", dest="optimize_option",
                         help="Set optimization level for {LLC_,LLI_,}OPTFLAGS",
                         choices=('-O0','-O1','-O2','-O3','-Os'), default='-O3')
        group.add_option("", "--cflag", dest="cflags",
                         help="Additional flags to set in TARGET_FLAGS",
                         action="append", type=str, default=[], metavar="FLAG")
        parser.add_option_group(group)

        group = OptionGroup(parser, "Test Selection")
        group.add_option("", "--simple", dest="test_simple",
                         help="Use TEST=simple instead of TEST=nightly",
                         action="store_true", default=False)

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
        parser.add_option_group(group)

        group = OptionGroup(parser, "Test Execution")
        group.add_option("-j", "--threads", dest="threads",
                         help="Number of testing threads",
                         type=int, default=1, metavar="N")

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
        parser.add_option_group(group)

        group = OptionGroup(parser, "Output Options")
        group.add_option("", "--no-auto-name", dest="auto_name",
                         help="Don't automatically derive submission name",
                         action="store_false", default=True)
        parser.add_option("", "--run-order", dest="run_order", metavar="STR",
                          help="String to use to identify and order this run",
                          action="store", type=str, default=None)
        parser.add_option_group(group)

        (opts, args) = parser.parse_args(args)
        if len(args) != 1:
            parser.error("invalid number of arguments")

        nick, = args

        # Validate options.

        if opts.sandbox_path is None:
            parser.error('--sandbox is required')

        if opts.test_simple:
            # TEST=simple doesn't use a reference compiler.
            if opts.cc_reference is not None:
                parser.error('--cc-reference is unused with --simple')
            if opts.cxx_reference is not None:
                parser.error('--cxx-reference is unused with --simple')
        else:
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

        if opts.llvm_src_root is None:
            parser.error('--llvm-src is required')
        if opts.llvm_obj_root is None:
            parser.error('--llvm-obj is required')
        if opts.test_suite_root is None:
            parser.error('--test-suite is required')

        if opts.remote:
            if opts.remote_port is None:
                parser.error('--remote-port is required with --remote')
            if opts.remote_user is None:
                parser.error('--remote-user is required with --remote')

        # FIXME: We need to validate that there is no configured output in the
        # test-suite directory, that borks things. <rdar://problem/7876418>

        return run_test(nick, opts)

def create_instance():
    return NTTest()

__all__ = ['create_instance']
