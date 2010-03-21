#!/usr/bin/env python

import re

kDataKeyStart = re.compile('(.*)  =>(.*)')

def loadSentData(path):
    def parseDGResults(text):
        results = {}
        if 'Dejagnu skipped by user choice' in text:
            return results
        for ln in text.strip().split('\n'):
            result,value = ln.split(':',1)
            results[result] = results.get(result,[])
            results[result].append(value)
        return results

    basename = 'nightlytest'

    # Guess the format (server side or client side) based on the first
    # character.
    isServerSide = (open(path).read(1) == '\'')

    f = open(path)
    data = {}

    current = None
    inData = False
    for ln in f:
        if inData:
            if ln == 'EOD\n':
                inData = False
            else:
                data[current] += ln
            continue

        m = kDataKeyStart.match(ln)
        if m:
            current,value = m.groups()
            if isServerSide:
                assert current[0] == current[-1] == "'"
                current = current[1:-1]
                assert value[0] == value[1] == ' '
                value = value[2:]
                if value == '<<EOD':
                    value = ''
                    inData = True
                else:
                    assert value[0] == value[-2] == '"'
                    assert value[-1] == ','
                    value = value[1:-2]
            data[current] = value
        elif isServerSide:
            assert ln == ',\n'
        else:
            assert current is not None
            data[current] += ln

    # Things we are ignoring for now
    data.pop('a_file_sizes')
    data.pop('all_tests')
    data.pop('build_data')
    data.pop('cvs_dir_count')
    data.pop('cvs_file_count')
    data.pop('cvsaddedfiles')
    data.pop('cvsmodifiedfiles')
    data.pop('cvsremovedfiles')
    data.pop('cvsusercommitlist')
    data.pop('cvsuserupdatelist')
    data.pop('dejagnutests_log')
    data.pop('expfail_tests')
    data.pop('lines_of_code')
    data.pop('llcbeta_options')
    data.pop('new_tests')
    data.pop('o_file_sizes')
    data.pop('passing_tests')
    data.pop('removed_tests')
    data.pop('target_triple')
    data.pop('unexpfail_tests')
    data.pop('warnings')
    data.pop('warnings_added')
    data.pop('warnings_removed')

    starttime = data.pop('starttime').strip()
    endtime = data.pop('endtime').strip()

    nickname = data.pop('nickname').strip()
    machine_data = data.pop('machine_data').strip()
    buildstatus = data.pop('buildstatus').strip()
    configtime_user = data.pop('configtime_cpu')
    configtime_wall = data.pop('configtime_wall')
    checkouttime_user = data.pop('cvscheckouttime_cpu')
    checkouttime_wall = data.pop('cvscheckouttime_wall')
    dgtime_user = data.pop('dejagnutime_cpu')
    dgtime_wall = data.pop('dejagnutime_wall')
    buildtime_wall = float(data.pop('buildtime_wall').strip())
    buildtime_user = float(data.pop('buildtime_cpu').strip())
    gcc_version = data.pop('gcc_version')
    dejagnutests_results = data.pop('dejagnutests_results')
    multisource = data.pop('multisource_programstable')
    singlesource = data.pop('singlesource_programstable')
    externals = data.pop('externalsource_programstable')

    assert not data.keys()

    machine = { 'Name' : nickname,
                'Info' : { 'gcc_version' : gcc_version } }
    for ln in machine_data.split('\n'):
        ln = ln.strip()
        if not ln:
            continue
        assert ':' in ln
        key,value = ln.split(':',1)
        machine['Info'][key] = value

    # We definitely don't want these in the machine data.
    if 'time' in machine['Info']:
        machine['Info'].pop('time')
    if 'date' in machine['Info']:
        machine['Info'].pop('date')

    run = { 'Start Time' : starttime,
            'End Time' : endtime,
            'Info' : { 'tag' : 'nightlytest' } }

    tests = []

    groupInfo = []

    # llvm-test doesn't provide this
    infoData = {}

    # Summary test information
    tests.append( { 'Name' : basename + '.Summary.configtime.wall',
                    'Info' : infoData,
                    'Data' : [configtime_wall] } )
    tests.append( { 'Name' : basename + '.Summary.configtime.user',
                    'Info' : infoData,
                    'Data' : [configtime_user] } )
    tests.append( { 'Name' : basename + '.Summary.checkouttime.wall',
                    'Info' : infoData,
                    'Data' : [checkouttime_wall] } )
    tests.append( { 'Name' : basename + '.Summary.checkouttime.user',
                    'Info' : infoData,
                    'Data' : [checkouttime_user] } )
    tests.append( { 'Name' : basename + '.Summary.buildtime.wall',
                    'Info' : infoData,
                    'Data' : [buildtime_wall] } )
    tests.append( { 'Name' : basename + '.Summary.buildtime.user',
                    'Info' : infoData,
                    'Data' : [buildtime_user] } )
    tests.append( { 'Name' : basename + '.Summary.dgtime.wall',
                    'Info' : infoData,
                    'Data' : [dgtime_wall] } )
    tests.append( { 'Name' : basename + '.Summary.dgtime.user',
                    'Info' : infoData,
                    'Data' : [dgtime_user] } )
    tests.append( { 'Name' : basename + '.Summary.buildstatus',
                    'Info' : infoData,
                    'Data' : [buildstatus == 'OK'] } )

    # DejaGNU Info
    results = parseDGResults(dejagnutests_results)
    for name in ('PASS', 'FAIL', 'XPASS', 'XFAIL'):
        tests.append( { 'Name' : basename + '.DejaGNU.' + name,
                        'Info' : infoData,
                        'Data' : [len(results.get(name,[]))] } )

    # llvm-test results
    groupInfo.append( { 'Name' : basename,
                        'Primary' : 1 } )
    for groupname,data in (('SingleSource', singlesource),
                           ('MultiSource', multisource),
                           ('Externals', externals)):
        groupInfo.append( { 'Name' : basename + '.' + groupname,
                            'Primary' : 1 } )
        lines = data.split('\n')
        header = lines[0].strip().split(',')
        for ln in lines[1:]:
            ln = ln.strip()
            if not ln:
                continue
            entry = dict([(k,v.strip())
                           for k,v in zip(header, ln.split(','))])
            testname = basename + '.%s/%s' % (groupname,
                                              entry['Program'].replace('.','_'))
            groupInfo.append( { 'Name' : testname,
                                'Primary' : 1 } )

            for name,key,tname in (('gcc.compile', 'GCCAS', 'time'),
                                   ('bc.compile', 'Bytecode', 'size'),
                                   ('llc.compile', 'LLC compile', 'time'),
                                   ('llc-beta.compile', 'LLC-BETA compile', 'time'),
                                   ('jit.compile', 'JIT codegen', 'time'),
                                   ('gcc.exec', 'GCC', 'time'),
                                   ('cbe.exec', 'CBE', 'time'),
                                   ('llc.exec', 'LLC', 'time'),
                                   ('llc-beta.exec', 'LLC-BETA', 'time'),
                                   ('jit.exec', 'JIT', 'time'),
                             ):
                time = entry[key]
                if time == '*':
                    tests.append( { 'Name' : testname + '.%s.success' % name,
                                    'Info' : infoData,
                                    'Data' : [0] } )
                else:
                    tests.append( { 'Name' : testname + '.%s.success' % name,
                                    'Info' : infoData,
                                    'Data' : [1] } )
                    tests.append( { 'Name' : testname + '.%s.%s' % (name, tname),
                                    'Info' : infoData,
                                    'Data' : [float(time)] } )
        pass

    return { 'Machine' : machine,
             'Run' : run,
             'Tests' : tests,
             'Group Info' : groupInfo }

def convertNTData(inputPath, outputPath):
    """convertNTData - Convert a nightlytest "sentdata.txt" file into a zorg
    plist file."""
    import plistlib

    data = loadSentData(inputPath)
    plistlib.writePlist(data, outputPath)

def main():
    global opts
    from optparse import OptionParser
    parser = OptionParser("usage: %prog file output")
    opts,args = parser.parse_args()

    if len(args) != 2:
        parser.error("incorrect number of argments")

    file,output = args

    convertNTData(file, output)

if __name__=='__main__':
    main()
