This directory contains a working skeleton for setting up a buildbot system
for testing LLVM.

Actually, there are is a generic working skeleton, in 'smooshlab', and
a specific working skeleton in 'osuosl' for talking to the public LLVM
buildbot hosted on lab.llvm.org.

Build Slaves
------------
These are the steps to install a buildslave based on this skeleton:

 1. Install buildbot.

 2. Create a user for the buildslave, e.g. "buildslave".

 3. Check out the "zorg" SVN module somewhere as the buildslave user, 
    e.g. ~buildslave/zorg.

 4. Edit "zorg/buildbot/osuosl/Config.py" and fix the buildslave name
    and password to match what the master expects.

 5. Add host information (e.g., 'uname -a') to info/host in the slave
    directory.

 6. Configure your system to start the buildbot automatically. On Mac
    OS X this means copying the sample .plist to /Library/LaunchDaemons
    (editing it as appropriate if the user name or slave directories are
    different), and using 'launchctl' to load and start it.
