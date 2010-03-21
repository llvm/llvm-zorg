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

def loadData(path):
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

def main():
    import plistlib
    import sys

    global opts
    from optparse import OptionParser
    parser = OptionParser("usage: %prog raw-data-path output")
    opts,args = parser.parse_args()

    if len(args) != 2:
        parser.error("incorrect number of argments")

    file,output = args

    data = loadData(file)

    plistlib.writePlist(data, output)

if __name__=='__main__':
    main()
