This directory contains a working skeleton for setting up a buildbot system
for testing LLVM.

Build Slaves
------------
These are the steps to install a buildslave based on this skeleton:

 1. Install buildbot.

 2. Create a user for the buildslave, e.g. "buildslave".

 3. Check out the "zorg" SVN module somewhere as the buildslave user, 
    e.g. ~buildslave/zorg.

 4. Edit "zorg/buildbot/smooshlab/Config.py" and fix getBuildmasterHost to 
    return the correct host name. You may also need to fix the buildslave 
    name and password to match what the master expects.

 5. Configure your system to start the buildbot automatically. On Mac
    OS X this means copying the sample .plist to /Library/LaunchDaemons
    (editing it as appropriate if the user name or slave directories are
    different), and using 'launchctl' to load and start it.
