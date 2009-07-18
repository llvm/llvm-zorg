# Common configuration parameters (used by master and slaves).

def getBuildmasterHost():
    return '127.0.0.1'

def getBuildmasterPort():
    return 9990

# Slave configuration parameters.

def getBuildslaveName():
    import os

     # Use the hostname as the slave name.
    return os.uname()[1]

def getBuildslavePassword():
    return 'password'

# Master configuration parameters.

def getBuildbotName():
    return 'smooshlab'

def getBuildmasterWebPort():
    return 8010

def shouldTrackChanges():
    return True

def shouldTrackLLVM():
    return True

def shouldTrackClang():
    return True

def shouldTrackLLVMGCC():
    return True
