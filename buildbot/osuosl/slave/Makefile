# -*- makefile -*-

# This is a simple makefile which lives in a buildmaster/buildslave
# directory (next to the buildbot.tac file). It allows you to start/stop the
# master or slave in a launchd-friendly way by doing 'make start' or 'make stop'
# and includes some other targets for convenience.

start:
	launchctl start org.llvm.osuosl.slave

start-standalone:
	/usr/bin/twistd \
	  --nodaemon \
	  --python=buildbot.tac \
	  --logfile=twistd.log \
	  --prefix=osuosl

# This stops the buildbot cleanly so launchd will not restart it, use
# 'make start' to restart it correctly via launchctl
stop:
	buildbot stop .	

restart: stop start

# Reloads the master.cfg and associated files.
sighup:
	buildbot sighup .	

reconfig: sighup

checkconfig:
	buildbot checkconfig
