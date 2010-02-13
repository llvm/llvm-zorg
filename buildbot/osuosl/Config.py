# Common configuration parameters (used by master and slaves).

def getBuildmasterHost():
    return 'google1.osuosl.org'

def getBuildmasterPort():
    return 9990

# Slave configuration parameters.

def getBuildslaveName():
    raise NotImplementedError,'please update Config.py with the buildslave name'

def getBuildslavePassword():
    raise NotImplementedError,'please update Config.py with the buildslave password'

# Master configuration parameters.

def getBuildbotName():
    return 'llvmbb'

def getBuildmasterWebPort():
    return 8011

def shouldTrackChanges():
    return True

def shouldTrackLLVM():
    return True

def shouldTrackClang():
    return True

def shouldTrackLLVMGCC():
    return True
