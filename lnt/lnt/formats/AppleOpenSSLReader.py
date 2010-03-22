"""
Converter for a custom format with the output of OpenSSL test runs.
"""

import os

def parseOpenSSLFile(path):
    data = open(path).read()
    lines = list(open(path))
    lnfields = [ln.strip().split(':') for ln in lines]
    assert(lnfields[0][0] == '+H')
    header = lnfields[0]
    blockSizes = map(int, header[1:])

    # Cipher -> [(Block Size,Value)*]
    data = {}
    for fields in lnfields[1:]:
        # Ignore other fields
        if fields[0] != '+F':
            continue

        name = fields[2]
        countsPerBlock = fields[3:]
        assert len(countsPerBlock) == len(blockSizes)
        data[name] = [(b,float(c))
                      for b,c in zip(blockSizes,countsPerBlock)]

    return data

def _matches_format(path_or_file):
    # If this is a file, we definitely can't load it.
    if not isinstance(path_or_file,str):
        return False

    # Assume an input matches this format if any of the key files exists.
    return (os.path.exists(os.path.join(path_or_file, 'svn-revision')) or
            os.path.exists(os.path.join(path_or_file, 'start.timestamp')) or
            os.path.exists(os.path.join(path_or_file, 'finished.timestamp')))
                     
def _load_data(path):
    # Look for svn-revision and timestamps.

    llvmRevision = ''
    startTime = endTime = ''

    f = os.path.join(path, 'svn-revision')
    if os.path.exists(f):
        svnRevisionData = open(f).read()
        assert(svnRevisionData[0] == 'r')
        llvmRevision = int(svnRevisionData[1:])

    f = os.path.join(path, 'start.timestamp')
    if os.path.exists(f):
        startTime = open(f).read().strip()

    f = os.path.join(path, 'finished.timestamp')
    if os.path.exists(f):
        endTime = open(f).read().strip()

    # Look for sub directories
    openSSLData = []
    for file in os.listdir(path):
        p = os.path.join(path, file)
        if os.path.isdir(p):
            # Look for Tests/Apple.OpenSSL.64/speed.txt
            p = os.path.join(p, 'Tests/Apple.OpenSSL.64/speed.txt')
            if os.path.exists(p):
                openSSLData.append((file, parseOpenSSLFile(p)))

    basename = 'apple_openssl'

    machine = { 'Name' : 'dgohman.apple.com',
                'Info' : {  } }

    run = { 'Start Time' : startTime,
            'End Time' : endTime,
            'Info' : { 'llvm-revision' : llvmRevision,
                       'tag' : 'apple_openssl' } }

    tests = []
    groupInfo = []

    for dirName,dirData in openSSLData:
        # Demangle compiler & flags
        if dirName.startswith('gcc'):
            compiler = 'gcc'
        elif dirName.startswith('llvm-gcc'):
            compiler = 'llvm-gcc'
        else:
            raise ValueError,compiler
        assert dirName[len(compiler)] == '-'
        flags = dirName[len(compiler)+1:]

        for cipher,values in dirData.items():
            testName = basename + '.' + cipher + '.ips'
            for block,value in values:
                parameters = { 'blockSize' : block,
                               'compiler' : compiler,
                               'compiler_flags' : flags }
                tests.append( { 'Name' : testName,
                                'Info' : parameters,
                                'Data' : [value] } )

    return { 'Machine' : machine,
             'Run' : run,
             'Tests' : tests,
             'Group Info' : groupInfo }

format = { 'name' : 'apple_openssl',
           'predicate' : _matches_format,
           'read' : _load_data }
