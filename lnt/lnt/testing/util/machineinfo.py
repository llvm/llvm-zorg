"""
Utilities for gathering information on the host machine for inclusion with
results.
"""

import re

from lnt.testing.util.commands import capture

# All the things we care to probe about the system, and whether to track with
# the machine or run. This is a list of (sysctl, kind) where kind is one of:
#  machine - key should always be part of machine
#  machdep - key should be part of machine, unless --no-machdep-info is set
#  run     - key should always be part of run
sysctl_info_table = [
    ('hw.activecpu',                              'machine'),
    ('hw.availcpu',                               'machine'),
    ('hw.busfrequency',                           'machine'),
    ('hw.busfrequency_max',                       'machine'),
    ('hw.busfrequency_min',                       'machine'),
    ('hw.byteorder',                              'machine'),
    ('hw.cacheconfig',                            'machine'),
    ('hw.cachelinesize',                          'machine'),
    ('hw.cachesize',                              'machine'),
    ('hw.cpu64bit_capable',                       'machine'),
    ('hw.cpufamily',                              'machine'),
    ('hw.cpufrequency',                           'machine'),
    ('hw.cpufrequency_max',                       'machine'),
    ('hw.cpufrequency_min',                       'machine'),
    ('hw.cpusubtype',                             'machine'),
    ('hw.cputype',                                'machine'),
    ('hw.epoch',                                  'machine'),
    ('hw.l1dcachesize',                           'machine'),
    ('hw.l1icachesize',                           'machine'),
    ('hw.l2cachesize',                            'machine'),
    ('hw.l2settings',                             'machine'),
    ('hw.logicalcpu',                             'machine'),
    ('hw.logicalcpu_max',                         'machine'),
    ('hw.machine',                                'machine'),
    ('hw.memsize',                                'machine'),
    ('hw.model',                                  'machine'),
    ('hw.ncpu',                                   'machine'),
    ('hw.optional.floatingpoint',                 'machine'),
    ('hw.optional.mmx',                           'machine'),
    ('hw.optional.sse',                           'machine'),
    ('hw.optional.sse2',                          'machine'),
    ('hw.optional.sse3',                          'machine'),
    ('hw.optional.sse4_1',                        'machine'),
    ('hw.optional.sse4_2',                        'machine'),
    ('hw.optional.supplementalsse3',              'machine'),
    ('hw.optional.x86_64',                        'machine'),
    ('hw.packages',                               'machine'),
    ('hw.pagesize',                               'machine'),
    ('hw.physicalcpu',                            'machine'),
    ('hw.physicalcpu_max',                        'machine'),
    ('hw.physmem',                                'machine'),
    ('hw.tbfrequency',                            'machine'),
    ('hw.usermem',                                'run'    ),
    ('hw.vectorunit',                             'machine'),
    ('kern.aiomax',                               'machine'),
    ('kern.aioprocmax',                           'machine'),
    ('kern.aiothreads',                           'machine'),
    ('kern.argmax',                               'machine'),
    ('kern.boottime',                             'run'    ),
    ('kern.clockrate: hz',                        'machine'),
    ('kern.coredump',                             'machine'),
    ('kern.corefile',                             'machine'),
    ('kern.delayterm',                            'machine'),
    ('kern.hostid',                               'machine'),
    ('kern.hostname',                             'machdep'),
    ('kern.job_control',                          'machine'),
    ('kern.maxfiles',                             'machine'),
    ('kern.maxfilesperproc',                      'machine'),
    ('kern.maxproc',                              'machine'),
    ('kern.maxprocperuid',                        'machine'),
    ('kern.maxvnodes',                            'machine'),
    ('kern.netboot',                              'machine'),
    ('kern.ngroups',                              'machine'),
    ('kern.nisdomainname',                        'machine'),
    ('kern.nx',                                   'machine'),
    ('kern.osrelease',                            'machine'),
    ('kern.osrevision',                           'machine'),
    ('kern.ostype',                               'machine'),
    ('kern.osversion',                            'machine'),
    ('kern.posix1version',                        'machine'),
    ('kern.procname',                             'machine'),
    ('kern.rage_vnode',                           'machine'),
    ('kern.safeboot',                             'machine'),
    ('kern.saved_ids',                            'machine'),
    ('kern.securelevel',                          'machine'),
    ('kern.shreg_private',                        'machine'),
    ('kern.speculative_reads_disabled',           'machine'),
    ('kern.sugid_coredump',                       'machine'),
    ('kern.thread_name',                          'machine'),
    ('kern.usrstack',                             'run'),
    ('kern.usrstack64',                           'run'),
    ('kern.version',                              'machine'),
    ('machdep.cpu.address_bits.physical',         'machine'),
    ('machdep.cpu.address_bits.virtual',          'machine'),
    ('machdep.cpu.arch_perf.events',              'machine'),
    ('machdep.cpu.arch_perf.events_number',       'machine'),
    ('machdep.cpu.arch_perf.fixed_number',        'machine'),
    ('machdep.cpu.arch_perf.fixed_width',         'machine'),
    ('machdep.cpu.arch_perf.number',              'machine'),
    ('machdep.cpu.arch_perf.version',             'machine'),
    ('machdep.cpu.arch_perf.width',               'machine'),
    ('machdep.cpu.brand',                         'machine'),
    ('machdep.cpu.brand_string',                  'machine'),
    ('machdep.cpu.cache.L2_associativity',        'machine'),
    ('machdep.cpu.cache.linesize',                'machine'),
    ('machdep.cpu.cache.size',                    'machine'),
    ('machdep.cpu.core_count',                    'machine'),
    ('machdep.cpu.cores_per_package',             'machine'),
    ('machdep.cpu.extfamily',                     'machine'),
    ('machdep.cpu.extfeature_bits',               'machine'),
    ('machdep.cpu.extfeatures',                   'machine'),
    ('machdep.cpu.extmodel',                      'machine'),
    ('machdep.cpu.family',                        'machine'),
    ('machdep.cpu.feature_bits',                  'machine'),
    ('machdep.cpu.features',                      'machine'),
    ('machdep.cpu.logical_per_package',           'machine'),
    ('machdep.cpu.max_basic',                     'machine'),
    ('machdep.cpu.max_ext',                       'machine'),
    ('machdep.cpu.microcode_version',             'machine'),
    ('machdep.cpu.model',                         'machine'),
    ('machdep.cpu.mwait.extensions',              'machine'),
    ('machdep.cpu.mwait.linesize_max',            'machine'),
    ('machdep.cpu.mwait.linesize_min',            'machine'),
    ('machdep.cpu.mwait.sub_Cstates',             'machine'),
    ('machdep.cpu.signature',                     'machine'),
    ('machdep.cpu.stepping',                      'machine'),
    ('machdep.cpu.thermal.ACNT_MCNT',             'machine'),
    ('machdep.cpu.thermal.dynamic_acceleration',  'machine'),
    ('machdep.cpu.thermal.sensor',                'machine'),
    ('machdep.cpu.thermal.thresholds',            'machine'),
    ('machdep.cpu.thread_count',                  'machine'),
    ('machdep.cpu.tlb.data.large',                'machine'),
    ('machdep.cpu.tlb.data.large_level1',         'machine'),
    ('machdep.cpu.tlb.data.small',                'machine'),
    ('machdep.cpu.tlb.data.small_level1',         'machine'),
    ('machdep.cpu.tlb.inst.large',                'machine'),
    ('machdep.cpu.tlb.inst.small',                'machine'),
    ('machdep.cpu.vendor',                        'machine'),
    ]

def _get_mac_addresses():
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

def get_machine_information(use_machine_dependent_info = False):
    machine_info = {}
    run_info = {}

    info_targets = {
        'machdep' : (run_info, machine_info)[
            use_machine_dependent_info],
        'machine' : machine_info,
        'run' : run_info }
    for name,target in sysctl_info_table:
        info_targets[target][name] = capture(['sysctl','-n',name],
                                             include_stderr=True).strip()

    for ifc,addr in _get_mac_addresses():
        # Ignore virtual machine mac addresses.
        if ifc.startswith('vmnet'):
            continue

        info_targets['machdep']['mac_addr.%s' % ifc] = addr

    return machine_info, run_info
