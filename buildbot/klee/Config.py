# Common configuration parameters (used by master and slaves).

def getBuildmasterHost():
    return 'klee.minormatter.com'

def getBuildmasterPort():
    return 9990

# Slave configuration parameters.

def getBuildslaveName():
    raise NotImplementedError,'please update Config.py with the buildslave name'

def getBuildslavePassword():
    raise NotImplementedError,'please update Config.py with the buildslave password'

# Master configuration parameters.

def getBuildbotName():
    return 'kleebb'

def getBuildmasterWebPort():
    return 8010
