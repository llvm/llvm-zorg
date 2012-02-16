import errno
import os
import pprint
import re
import shlex
import subprocess
import sys

import lnt.testing
import lnt.testing.util.compilers
from lnt.testing.util.commands import note, warning, error, fatal
from lnt.testing.util.commands import capture, rm_f
from lnt.testing.util.misc import timestamp

# Interface to runN.
#
# FIXME: Simplify.
#
# FIXME: Figure out a better way to deal with need to run as root.
def runN(args, N, cwd, preprocess_cmd=None, env=None, sample_mem=False,
         ignore_stderr=False):
    cmd = ['runN', '-a']
    if sample_mem:
        cmd = ['sudo'] + cmd + ['-m']
    if preprocess_cmd is not None:
        cmd.append('-p', preprocess_cmd)
    cmd.append(str(int(N)))
    cmd.extend(args)

    if opts.verbose:
        note("running %r" % cmd)
    p = subprocess.Popen(args=cmd,
                         stdin=None,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.PIPE,
                         env=env,
                         cwd=cwd)
    stdout,stderr = p.communicate()
    res = p.wait()

    data = None
    try:
        data = eval(stdout)
    except:
        error("failed to parse output: %s\n" % stdout)

    if not ignore_stderr and stderr.strip():
        error("stderr isn't empty: %s\n" % stderr)
        data = None

    if res:
        error("res != 0: %s\n" % res)
        data = None

    return data

# Test functions.
def get_input_path(opts, *names):
    return os.path.join(opts.test_suite_externals, "lnt-compile-suite-src",
                        *names)

def get_output_path(name):
    return os.path.join(g_output_dir, name)

def get_runN_test_data(name, variables, cmd, ignore_stderr=False,
                       sample_mem=False, only_mem=False):
    if only_mem and not sample_mem:
        raise ArgumentError,"only_mem doesn't make sense without sample_mem"

    data = runN(cmd, variables.get('run_count'), cwd='/tmp',
                ignore_stderr=ignore_stderr, sample_mem=sample_mem)
    if data is not None:
        if data.get('version') != 0:
            raise ValueError,'unknown runN data format'
        data_samples = data.get('samples')
    keys = []
    if not only_mem:
        keys.extend([('user',1),('sys',2),('wall',3)])
    if sample_mem:
        keys.append(('mem',4))
    for key,idx in keys:
        tname = '%s.%s' % (name,key)
        success = False
        samples = []
        if data is not None:
            success = True
            samples = [sample[idx] for sample in data_samples]
        yield (success, tname, samples)

# FIXME: Encode dependency on output automatically, for simpler test execution.
def test_cc_command(base_name, run_info, variables, input, output, flags,
                    extra_flags, has_output=True, ignore_stderr=False,
                    can_memprof=True):
    name = '%s.flags=%s' % (base_name,' '.join(flags),)
    input = get_input_path(opts, input)
    output = get_output_path(output)

    cmd = [variables.get('cc')]
    cmd.extend(extra_flags)
    cmd.append(input)
    cmd.extend(flags)

    # FIXME: Probably a bad idea, but its not worth worry about test failures
    # for compiler versions which emit warnings on the test inputs for now.
    cmd.append('-w')

    # Do a memory profiling run, if requested.
    #
    # FIXME: Doing this as a separate step seems silly. We shouldn't do any
    # extra run just to get the memory statistics.
    if can_memprof and opts.memory_profiling:
        # Find the cc1 command, which we use to do memory profiling. To do this
        # we execute the compiler with '-###' to figure out what it wants to do.
        cc_output = capture(cmd + ['-o','/dev/null','-###'],
                            include_stderr=True).strip()
        cc_commands = []
        for ln in cc_output.split('\n'):
            # Filter out known garbage.
            if (ln == 'Using built-in specs.' or
                ln.startswith('Configured with:') or
                ln.startswith('Target:') or
                ln.startswith('Thread model:') or
                ' version ' in ln):
                continue
            cc_commands.append(ln)

        if len(cc_commands) != 1:
            fatal('unable to determine cc1 command: %r' % cc_output)

        cc1_cmd = shlex.split(cc_commands[0])
        for res in get_runN_test_data(name, variables, cc1_cmd,
                                      ignore_stderr=ignore_stderr,
                                      sample_mem=True, only_mem=True):
            yield res

    rm_f(output)
    for res in get_runN_test_data(name, variables, cmd + ['-o',output],
                                  ignore_stderr=ignore_stderr):
        yield res

    # If the command has output, track its size.
    if has_output:
        tname = '%s.size' % (name,)
        success = False
        samples = []
        try:
            stat = os.stat(output)
            success = True
            samples.append(stat.st_size)
        except OSError,e:
            if e.errno != errno.ENOENT:
                raise
        yield (success, tname, samples)

def test_compile(name, run_info, variables, input, output, pch_input,
                 flags, stage, extra_flags=[]):
    extra_flags = list(extra_flags)

    cc_name = variables.get('cc_name')
    is_llvm = not (cc_name == 'gcc')
    is_clang = not (cc_name in ('gcc', 'llvm-gcc'))

    # Ignore irgen stages for non-LLVM compilers.
    if not is_llvm and stage in ('irgen', 'irgen_only',):
        return ()

    # Ignore 'init' and 'irgen_only' stages for non-Clang.
    if not is_clang and stage in ('init', 'irgen_only'):
        return ()

    # Force gnu99 mode for all compilers.
    if not is_clang:
        extra_flags.append('-std=gnu99')

    stage_flags,has_output = { 'pch-gen' : (('-x','objective-c-header'),True),
                               'driver' : (('-###','-fsyntax-only'), False),
                               'init' : (('-fsyntax-only',
                                          '-Xclang','-init-only'),
                                         False),
                               'syntax' : (('-fsyntax-only',), False),
                               'irgen_only' : (('-emit-llvm','-c',
                                                '-Xclang','-emit-llvm-only'),
                                               False),
                               'irgen' : (('-emit-llvm','-c'), True),
                               'codegen' : (('-S',), True),
                               'assembly' : (('-c',), True), }[stage]

    # Ignore stderr output (instead of failing) in 'driver' stage, -### output
    # goes to stderr by default.
    ignore_stderr = stage == 'driver'

    # We can't memory profile an assembly command.
    #
    # FIXME: Actually, we can with -integrated-as.
    can_memprof = stage != 'assembly'

    extra_flags.extend(stage_flags)
    if pch_input is not None:
        assert pch_input.endswith('.gch')
        extra_flags.extend(['-include', get_output_path(pch_input[:-4])])

    extra_flags.extend(['-I', os.path.dirname(get_input_path(opts, input))])

    return test_cc_command(name, run_info, variables, input, output, flags,
                           extra_flags, has_output, ignore_stderr, can_memprof)

# Build the test map.
def curry(fn, **kw_args):
    return lambda *args: fn(*args, **kw_args)

g_output_dir = None
all_inputs = [('Sketch/Sketch+Accessibility/SKTGraphicView.m', True, ()),
              ('403.gcc/combine.c', False, ('-DSPEC_CPU_MACOSX',))]

flags_to_test = [('-O0',), ('-O0','-g',), ('-Os',)]
stages_to_test = ['driver', 'init', 'syntax', 'irgen_only', 'irgen', 'codegen',
                  'assembly']
all_tests = []
for f in flags_to_test:
    # FIXME: Note that the order matters here, because we need to make sure to
    # generate the right PCH file before we try to use it. Ideally the testing
    # infrastructure would just handle this.
    all_tests.append(('pch-gen/Cocoa',
                      curry(test_compile, input='Cocoa_Prefix.h',
                            output='Cocoa_Prefix.h.gch', pch_input=None, flags=f,
                            stage='pch-gen')))
    for input,uses_pch,extra_flags in all_inputs:
        name = os.path.dirname(input)
        output = os.path.splitext(os.path.basename(input))[0] + '.o'
        for stage in stages_to_test:
            pch_input = None
            if uses_pch:
                pch_input = 'Cocoa_Prefix.h.gch'
            all_tests.append(('compile/%s/%s' % (name.replace('.','_'), stage),
                              curry(test_compile, input=input, output=output,
                                    pch_input=pch_input, flags=f, stage=stage,
                                    extra_flags=extra_flags)))

tests_by_name = dict([(k,(k,v)) for k,v in all_tests])

import platform
from datetime import datetime

# All the things we care to probe about the system, and whether to track with
# the machine or run. This is a list of (sysctl, kind) where kind is one of:
#  machine - key should always be part of machine
#  machdep - key should be part of machine, unless --no-machdep-info is set
#  run     - key should always be part of run
sysctl_info_table = [
    ('hw.activecpu',                              'machine'), # 8
    ('hw.availcpu',                               'machine'), # 8
    ('hw.busfrequency',                           'machine'), # 1600000000
    ('hw.busfrequency_max',                       'machine'), # 1600000000
    ('hw.busfrequency_min',                       'machine'), # 1600000000
    ('hw.byteorder',                              'machine'), # 1234
    ('hw.cacheconfig',                            'machine'), # 8 1 2 0 0 0 0 0 0 0
    ('hw.cachelinesize',                          'machine'), # 64
    ('hw.cachesize',                              'machine'), # 6442450944 32768 6291456 0 0 0 0 0 0 0
    ('hw.cpu64bit_capable',                       'machine'), # 1
    ('hw.cpufamily',                              'machine'), # 2028621756
    ('hw.cpufrequency',                           'machine'), # 2800000000
    ('hw.cpufrequency_max',                       'machine'), # 2800000000
    ('hw.cpufrequency_min',                       'machine'), # 2800000000
    ('hw.cpusubtype',                             'machine'), # 4
    ('hw.cputype',                                'machine'), # 7
    ('hw.epoch',                                  'machine'), # 0
    ('hw.l1dcachesize',                           'machine'), # 32768
    ('hw.l1icachesize',                           'machine'), # 32768
    ('hw.l2cachesize',                            'machine'), # 6291456
    ('hw.l2settings',                             'machine'), # 1
    ('hw.logicalcpu',                             'machine'), # 8
    ('hw.logicalcpu_max',                         'machine'), # 8
    ('hw.machine',                                'machine'), # i386
    ('hw.memsize',                                'machine'), # 6442450944
    ('hw.model',                                  'machine'), # MacPro3,1
    ('hw.ncpu',                                   'machine'), # 8
    ('hw.optional.floatingpoint',                 'machine'), # 1
    ('hw.optional.mmx',                           'machine'), # 1
    ('hw.optional.sse',                           'machine'), # 1
    ('hw.optional.sse2',                          'machine'), # 1
    ('hw.optional.sse3',                          'machine'), # 1
    ('hw.optional.sse4_1',                        'machine'), # 1
    ('hw.optional.sse4_2',                        'machine'), # 0
    ('hw.optional.supplementalsse3',              'machine'), # 1
    ('hw.optional.x86_64',                        'machine'), # 1
    ('hw.packages',                               'machine'), # 2
    ('hw.pagesize',                               'machine'), # 4096
    ('hw.physicalcpu',                            'machine'), # 8
    ('hw.physicalcpu_max',                        'machine'), # 8
    ('hw.physmem',                                'machine'), # 2147483648
    ('hw.tbfrequency',                            'machine'), # 1000000000
    ('hw.usermem',                                'run'    ), # 1347354624
    ('hw.vectorunit',                             'machine'), # 1
    ('kern.aiomax',                               'machine'), # 90
    ('kern.aioprocmax',                           'machine'), # 16
    ('kern.aiothreads',                           'machine'), # 4
    ('kern.argmax',                               'machine'), # 262144
    ('kern.boottime',                             'run'    ), # Tue Mar 23 18:36:38 2010
    ('kern.clockrate: hz',                        'machine'), # 100, tick = 10000, profhz = 100, stathz = 100
    ('kern.coredump',                             'machine'), # 1
    ('kern.corefile',                             'machine'), # /cores/core.%P
    ('kern.delayterm',                            'machine'), # 0
    ('kern.hostid',                               'machine'), # 0
    ('kern.hostname',                             'machdep'), # lordcrumb.apple.com
    ('kern.job_control',                          'machine'), # 1
    ('kern.maxfiles',                             'machine'), # 12288
    ('kern.maxfilesperproc',                      'machine'), # 10240
    ('kern.maxproc',                              'machine'), # 532
    ('kern.maxprocperuid',                        'machine'), # 266
    ('kern.maxvnodes',                            'machine'), # 99328
    ('kern.netboot',                              'machine'), # 0
    ('kern.ngroups',                              'machine'), # 16
    ('kern.nisdomainname',                        'machine'), #
    ('kern.nx',                                   'machine'), # 1
    ('kern.osrelease',                            'machine'), # 10.2.0
    ('kern.osrevision',                           'machine'), # 199506
    ('kern.ostype',                               'machine'), # Darwin
    ('kern.osversion',                            'machine'), # 10C540
    ('kern.posix1version',                        'machine'), # 200112
    ('kern.procname',                             'machine'), #
    ('kern.rage_vnode',                           'machine'), # 0
    ('kern.safeboot',                             'machine'), # 0
    ('kern.saved_ids',                            'machine'), # 1
    ('kern.securelevel',                          'machine'), # 0
    ('kern.shreg_private',                        'machine'), # 0
    ('kern.speculative_reads_disabled',           'machine'), # 0
    ('kern.sugid_coredump',                       'machine'), # 0
    ('kern.thread_name',                          'machine'), # kern
    ('kern.usrstack',                             'machine'), # 1606418432
    ('kern.usrstack64',                           'machine'), # 140734799806464
    ('kern.version',                              'machine'), # Darwin Kernel Version 10.2.0: Tue Nov 3 10:37:10 PST 2009; root:xnu-1486.2.11~1/RELEASE_I386
    ('machdep.cpu.address_bits.physical',         'machine'), # 38
    ('machdep.cpu.address_bits.virtual',          'machine'), # 48
    ('machdep.cpu.arch_perf.events',              'machine'), # 0
    ('machdep.cpu.arch_perf.events_number',       'machine'), # 7
    ('machdep.cpu.arch_perf.fixed_number',        'machine'), # 3
    ('machdep.cpu.arch_perf.fixed_width',         'machine'), # 40
    ('machdep.cpu.arch_perf.number',              'machine'), # 2
    ('machdep.cpu.arch_perf.version',             'machine'), # 2
    ('machdep.cpu.arch_perf.width',               'machine'), # 40
    ('machdep.cpu.brand',                         'machine'), # 0
    ('machdep.cpu.brand_string',                  'machine'), # Intel(R) Xeon(R) CPU E5462 @ 2.80GHz
    ('machdep.cpu.cache.L2_associativity',        'machine'), # 8
    ('machdep.cpu.cache.linesize',                'machine'), # 64
    ('machdep.cpu.cache.size',                    'machine'), # 6144
    ('machdep.cpu.core_count',                    'machine'), # 4
    ('machdep.cpu.cores_per_package',             'machine'), # 4
    ('machdep.cpu.extfamily',                     'machine'), # 0
    ('machdep.cpu.extfeature_bits',               'machine'), # 537921536 1
    ('machdep.cpu.extfeatures',                   'machine'), #  SYSCALL XD EM64T
    ('machdep.cpu.extmodel',                      'machine'), # 1
    ('machdep.cpu.family',                        'machine'), # 6
    ('machdep.cpu.feature_bits',                  'machine'), # 3219913727 844733
    ('machdep.cpu.features',                      'machine'), #  FPU VME DE PSE TSC MSR PAE MCE CX8  APIC SEP MTRR PGE MCA CMOV PAT PSE36 CLFSH DS ACPI MMX FXSR SSE SSE2 SS HTT TM SSE3 MON DSCPL VMX EST TM2 SSSE3 CX16 TPR PDCM SSE4.1
    ('machdep.cpu.logical_per_package',           'machine'), # 4
    ('machdep.cpu.max_basic',                     'machine'), # 10
    ('machdep.cpu.max_ext',                       'machine'), # 2147483656
    ('machdep.cpu.microcode_version',             'machine'), # 1547
    ('machdep.cpu.model',                         'machine'), # 23
    ('machdep.cpu.mwait.extensions',              'machine'), # 3
    ('machdep.cpu.mwait.linesize_max',            'machine'), # 64
    ('machdep.cpu.mwait.linesize_min',            'machine'), # 64
    ('machdep.cpu.mwait.sub_Cstates',             'machine'), # 8736
    ('machdep.cpu.signature',                     'machine'), # 67190
    ('machdep.cpu.stepping',                      'machine'), # 6
    ('machdep.cpu.thermal.ACNT_MCNT',             'machine'), # 1
    ('machdep.cpu.thermal.dynamic_acceleration',  'machine'), # 0
    ('machdep.cpu.thermal.sensor',                'machine'), # 1
    ('machdep.cpu.thermal.thresholds',            'machine'), # 2
    ('machdep.cpu.thread_count',                  'machine'), # 4
    ('machdep.cpu.tlb.data.large',                'machine'), # 16
    ('machdep.cpu.tlb.data.large_level1',         'machine'), # 32
    ('machdep.cpu.tlb.data.small',                'machine'), # 16
    ('machdep.cpu.tlb.data.small_level1',         'machine'), # 256
    ('machdep.cpu.tlb.inst.large',                'machine'), # 8
    ('machdep.cpu.tlb.inst.small',                'machine'), # 128
    ('machdep.cpu.vendor',                        'machine'), # GenuineIntel
    ]

def get_mac_addresses():
    lines = capture(['ifconfig']).strip()
    current_ifc = None
    for ln in lines.split('\n'):
        if ln.startswith('\t'):
            if current_ifc is None:
                fatal('unexpected ifconfig output')
            if ln.startswith('\tether '):
                yield current_ifc,ln[len('\tether '):].strip()
        else:
            current_ifc, = re.match(r'([A-Za-z0-9]*): .*', ln).groups()

###

import builtintest
from optparse import OptionParser, OptionGroup

usage_info = """
Script for testing a few simple dimensions of compile time performance
on individual files.

This is only intended to test the raw compiler performance, not its scalability
or its performance in parallel builds.

This tests:
 - PCH Generation for Cocoa.h
   o File Size
   o Memory Usage
   o Time
 - Objective-C Compile Time, with PCH
   o File Sizes
   o Memory Usage
   o Time
 - C Compile Time, without PCH
   o File Sizes
   o Memory Usage
   o Time

TODO:
 - Objective-C Compile Time, with PCH
   o PCH Utilization

FIXME: One major hole here is that we aren't testing one situation which does
sometimes show up with PCH, where we have a PCH file + a second significant body
of code (e.g., a large user framework, or a poorly PCHified project). In
practice, this can be a significant hole because PCH has a substantial impact on
how lookup, for example, is done.

We run each of the tests above in a number of dimensions:
 - O0
 - O0 -g
 - Os

We run each of the compile time tests in various stages:
 - ### (driver time)
 - init (driver + compiler init)
 - fsyntax-only (lex/parse/sema time)
 - emit-llvm-only (IRgen time)
 - emit-llvm (.bc output time and size, mostly to track output file size)
 - S (codegen time and size)
 - c (assembly time and size)
"""

class CompileTest(builtintest.BuiltinTest):
    def describe(self):
        return 'Single file compile-time performance testing'

    def run_test(self, name, args):
        global opts
        parser = OptionParser(
            ("%%prog %(name)s [options] [<output file>]\n" +
             usage_info) % locals())
        parser.add_option("-v", "--verbose", dest="verbose",
                          help="Show more test output",
                          action="store_true", default=False)
        parser.add_option("-s", "--sandbox", dest="sandbox_path",
                          help="Parent directory to build and run tests in",
                          type=str, default=None, metavar="PATH")

        group = OptionGroup(parser, "Test Options")
        group.add_option("", "--cc", dest="cc", type='str',
                         help="Compiler under test",
                         action="store", default=None)
        group.add_option("", "--test-externals", dest="test_suite_externals",
                         help="Path to the LLVM test-suite externals",
                         type=str, default=None, metavar="PATH")
        group.add_option("", "--machine-param", dest="machine_parameters",
                         metavar="NAME=VAL",
                         help="Add 'NAME' = 'VAL' to the machine parameters",
                         type=str, action="append", default=[])
        group.add_option("", "--run-param", dest="run_parameters",
                         metavar="NAME=VAL",
                         help="Add 'NAME' = 'VAL' to the run parameters",
                         type=str, action="append", default=[])
        group.add_option("", "--run-order", dest="run_order", metavar="STR",
                         help="String to use to identify and order this run",
                         action="store", type=str, default=None)
        parser.add_option_group(group)

        group = OptionGroup(parser, "Test Selection")
        group.add_option("", "--no-memory-profiling", dest="memory_profiling",
                         help="Disable memory profiling",
                         action="store_false", default=True)
        group.add_option("", "--multisample", dest="run_count", metavar="N",
                         help="Accumulate test data from multiple runs",
                         action="store", type=int, default=3)
        group.add_option("", "--test", dest="tests", metavar="NAME",
                         help="Individual test to run",
                         action="append", default=[],
                         choices=[k for k,v in all_tests])
        parser.add_option_group(group)

        group = OptionGroup(parser, "Output Options")
        group.add_option("", "--no-machdep-info", dest="machdep_info",
                         help=("Don't put machine (instance) dependent "
                               "variables in machine info"),
                         action="store_false", default=True)
        group.add_option("", "--machine-name", dest="machine_name", type='str',
                         help="Machine name to use in submission [%default]",
                         action="store", default=platform.uname()[1])
        parser.add_option_group(group)

        opts,args = parser.parse_args(args)

        if len(args) != 0:
            parser.error("invalid number of arguments")

        # Validate options.
        if opts.cc is None:
            parser.error('--cc is required')
        if opts.sandbox_path is None:
            parser.error('--sandbox is required')
        if opts.test_suite_externals is None:
            parser.error("--test-externals option is required")

        # Set up the sandbox.
        global g_output_dir
        if not os.path.exists(opts.sandbox_path):
            print >>sys.stderr, "%s: creating sandbox: %r" % (
                timestamp(), opts.sandbox_path)
            os.mkdir(opts.sandbox_path)
        g_output_dir = os.path.join(os.path.abspath(opts.sandbox_path),
                                    "test-%s" % (
                timestamp().replace(' ','_').replace(':','-'),))
        try:
            os.mkdir(g_output_dir)
        except OSError,e:
            if e.errno == errno.EEXIST:
                parser.error("sandbox output directory %r already exists!" % (
                        g_output_dir,))
            else:
                raise

        # Collect machine and run information.
        #
        # FIXME: Include information on test source versions.
        #
        # FIXME: Get more machine information? Cocoa.h hash, for example.
        machine_info = {}
        run_info = {}
        info_targets = { 'machdep' : (run_info,machine_info)[opts.machdep_info],
                         'machine' : machine_info,
                         'run' : run_info }
        for name,target in sysctl_info_table:
            info_targets[target][name] = capture(['sysctl','-n',name],
                                                 include_stderr=True).strip()

        for ifc,addr in get_mac_addresses():
            # Ignore virtual machine mac addresses.
            if ifc.startswith('vmnet'):
                continue

            info_targets['machdep']['mac_addr.%s' % ifc] = addr

        for name,cmd in (('sys_cc_version', ('/usr/bin/gcc','-v')),
                         ('sys_as_version', ('/usr/bin/as','-v','/dev/null')),
                         ('sys_ld_version', ('/usr/bin/ld','-v'))):
            run_info[name] = capture(cmd, include_stderr=True).strip()

        # Set command line machine and run information.
        for target,params in (('machine',opts.machine_parameters),
                              ('run',opts.run_parameters)):
            for entry in params:
                if '=' not in entry:
                    name,val = entry,''
                else:
                    name,val = entry.split('=', 1)
                info_targets[target][name] = val

        # Set user variables.
        variables = {}
        variables['cc'] = opts.cc
        variables['run_count'] = opts.run_count

        # Get compiler info.
        cc_info = lnt.testing.util.compilers.get_cc_info(variables['cc'])
        variables.update(cc_info)

        # Set the run order from the user, if given.
        if opts.run_order is not None:
            variables['run_order'] = opts.run_order
        else:
            # Otherwise, use the inferred run order.
            variables['run_order'] = cc_info['inferred_run_order']
            note("inferred run order to be: %r" % (variables['run_order'],))

        if opts.verbose:
            format = pprint.pformat(variables)
            msg = '\n\t'.join(['using variables:'] + format.splitlines())
            note(msg)

            format = pprint.pformat(machine_info)
            msg = '\n\t'.join(['using machine info:'] + format.splitlines())
            note(msg)

            format = pprint.pformat(run_info)
            msg = '\n\t'.join(['using run info:'] + format.splitlines())
            note(msg)

        # Find the tests to run.
        if not opts.tests:
            tests_to_run = list(all_tests)
        else:
            tests_to_run = [(k,v) for k,v in all_tests
                            if k in opts.tests]

        # Ensure output directory is available.
        if not os.path.exists(g_output_dir):
            os.mkdir(g_output_dir)

        # Execute the run.
        run_info.update(variables)
        run_info['tag'] = tag = 'compile'

        testsamples = []
        start_time = datetime.utcnow()
        print >>sys.stderr, '%s: run started' % start_time.strftime(
            '%Y-%m-%d %H:%M:%S')
        try:
            for basename,test_fn in tests_to_run:
                for success,name,samples in test_fn(basename, run_info,
                                                         variables):
                    print >>sys.stderr, '%s: collected sample: %r - %r' % (
                        datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                        name, samples)
                    test_name = '%s.%s' % (tag, name)
                    if not success:
                        testsamples.append(lnt.testing.TestSamples(
                                test_name + '.status', [lnt.testing.FAIL]))
                    if samples:
                        testsamples.append(lnt.testing.TestSamples(
                                test_name, samples))
        except KeyboardInterrupt:
            pass
        except:
            import traceback
            print >>sys.stderr,'*** EXCEPTION DURING TEST, HALTING ***'
            print >>sys.stderr,'--'
            traceback.print_exc()
            print >>sys.stderr,'--'
            run_info['had_errors'] = 1
        end_time = datetime.utcnow()
        print >>sys.stderr, '%s: run complete' % start_time.strftime(
            '%Y-%m-%d %H:%M:%S')

        # Package up the report.
        machine = lnt.testing.Machine(opts.machine_name, machine_info)
        run = lnt.testing.Run(start_time, end_time, info = run_info)

        return lnt.testing.Report(machine, run, testsamples)

def create_instance():
    return CompileTest()

__all__ = ['create_instance']
