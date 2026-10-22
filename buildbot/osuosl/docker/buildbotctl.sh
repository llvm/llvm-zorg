#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

# ${BUILDBOT_HOME}
# ${BUILDBOT_ZORG}
# ${BUILDBOT_CONFIG_DIR} - a path to master.cfg within ${BUILDBOT_ZORG}

# ${BUILDBOT_ZORG_URL}
# ${BUILDBOT_ZORG_BRANCH}

: "${BUILDBOT_HOME:=$HOME}"
: "${BUILDBOT_ZORG:=$BUILDBOT_HOME/llvm-zorg}"
: "${BUILDBOT_CONFIG_DIR:=$BUILDBOT_ZORG/buildbot/osuosl/master}"

#TODO:VV: replace with production values
: "${BUILDBOT_ZORG_URL:=https://github.com/vvereschaka/llvm-zorg.git}"
: "${BUILDBOT_ZORG_BRANCH:=llvm-buildbot/docker}"

echo "Buildbot working dir: $BUILDBOT_HOME"
echo "Buildbot LLVM Zorg dir: $BUILDBOT_ZORG"
echo "Buildbot config dir: $BUILDBOT_CONFIG_DIR"

cd $BUILDBOT_HOME

export PATH="$BUILDBOT_HOME/venv/bin:$PATH" 

check_init_zorg() {
    if [ ! -f "$BUILDBOT_ZORG/.git/config" ]
    then
        echo "No LLVM Zorg found at $BUILDBOT_ZORG. Checking it out ..."
        echo "LLVM Zorg URL/branch $BUILDBOT_ZORG_URL/$BUILDBOT_ZORG_BRANCH"
        echo "Note: the destination directory will completely wiped out before checkout."
        mkdir -p $BUILDBOT_ZORG
        pushd $BUILDBOT_ZORG
        # wipe out
        rm -rf * .*
        # checking out
        git clone -b $BUILDBOT_ZORG_BRANCH $BUILDBOT_ZORG_URL .
        popd
    else
        pushd $BUILDBOT_ZORG
        BUILDBOT_ZORG_URL=$(git remote get-url origin)
        BUILDBOT_ZORG_BRANCH=$(git branch --show-current)
        popd
        export BUILDBOT_ZORG_URL
        export BUILDBOT_ZORG_BRANCH
    fi

    BUILDBOT_BASEDIR="$BUILDBOT_CONFIG_DIR"
    export BUILDBOT_BASEDIR
    echo "BUILDBOT_BASEDIR: $BUILDBOT_BASEDIR"

    # Use default LLVM buildbot .cfg files inside of the docker image if none of them were provided.
    if [ ! -f "$BUILDBOT_BASEDIR/config/local.cfg" ]
    then
        ln -sf "$BUILDBOT_HOME/local.cfg" "$BUILDBOT_BASEDIR/config/local.cfg"
    fi
    if [ ! -f "$BUILDBOT_BASEDIR/config/worker-passwords.cfg" ]
    then
        ln -sf "$BUILDBOT_HOME/worker-passwords.cfg" "$BUILDBOT_BASEDIR/config/worker-passwords.cfg"
    fi
}

cmd_start() {
    check_init_zorg "$@"
    
    # Fixed buildbot master not start error in docker
    rm -f "$BUILDBOT_HOME/twistd.pid"
    # wait for db to start by trying to upgrade the master
    until buildbot upgrade-master "$BUILDBOT_BASEDIR"
    do
        echo "Can't upgrade master yet. Waiting for database ready?"
        sleep 1
    done

    # we use exec so that twistd use the pid 1 of the container, and so that signals are properly forwarded
    exec twistd -ny "$BUILDBOT_HOME/buildbot.tac"
}

cmd_stop() {
    if [ -f "$BUILDBOT_HOME/twistd.pid" ]
    then
        kill -1 $(cat $BUILDBOT_HOME/twistd.pid)
        rm -f "$BUILDBOT_HOME/twistd.pid"
    fi
}

cmd_restart() {    
    check_init_zorg "$@"

    cmd_stop
    
    exec twistd -ny "$BUILDBOT_HOME/buildbot.tac"
}

cmd_checkconfig() {
    check_init_zorg "$@"

    buildbot checkconfig "$BUILDBOT_BASEDIR"
}

cmd_updateconfig() {
    check_init_zorg "$@"

    #TODO:
    sleep 1
}

cmd_startworker() {
    BUILDBOT_BASEDIR="$BUILDBOT_HOME"
    export BUILDBOT_BASEDIR
    echo "BUILDBOT_BASEDIR: $BUILDBOT_BASEDIR"
    
    : "${DUMB_WORKER_DIR:=$HOME/dumb-worker}" 

    if [ -f "$DUMB_WORKER_DIR/bin/dumb-util.sh" ]
    then
        export PATH="$DUMB_WORKER_DIR/bin:$PATH" 
    fi

    if [ -f "$BUILDBOT_HOME/gethostinfo.py" ]
    then
        # Rebuild the host information for the worker.
        mkdir -p "$BUILDBOT_HOME/info"
        python3 "$BUILDBOT_HOME/gethostinfo.py" "$BUILDBOT_HOME/info/host"
    fi
    
    exec $BUILDBOT_HOME/venv/bin/twistd --pidfile= -ny buildbot.tac
}

usage() {
    echo "Usage: $0 {start|restart|stop|checkconfig|updateconfig|start-worker} [options]"
    echo "Commands:"
    echo "  start           Start LLVM Buildbot"
    echo "  stop            Stop LLVM Buildbot"
    echo "  checkconfig     Check existing LLVM Zorg configuration"
    echo "  updateconfig    Check out configuration updates and reload them."
    echo "  start-worker    Start LLVM Buildbot worker within the docker container."
    
    echo ""
    echo "BUILDBOT_HOME:        $BUILDBOT_HOME"
    echo "BUILDBOT_ZORG:        $BUILDBOT_ZORG"
    echo "BUILDBOT_ZORG_URL:    $BUILDBOT_ZORG_URL"
    echo "BUILDBOT_ZORG_BRANCH: $BUILDBOT_ZORG_BRANCH"
    echo "BUILDBOT_CONFIG_DIR:  $BUILDBOT_CONFIG_DIR"
    echo "BUILDBOT_BASEDIR:     $BUILDBOT_BASEDIR"
    
    exit 1
}

# 1. Ensure at least one argument (the command) is provided
if [[ $# -lt 1 ]]; then
    usage
fi

# Extract the main internal command
COMMAND="$1"
shift # Remove the command name from the argument list ($@)

# Route to the internal command safely
case "$COMMAND" in
    start)
        cmd_start "$@" # Pass all remaining arguments securely
        ;;
    restart)
        cmd_restart "$@"
        ;;
    stop)
        cmd_stop "$@"
        ;;
    checkconfig)
        cmd_checkconfig "$@"
        ;;
    updateconfig)
        cmd_updateconfig "$@"
        ;;
    start-worker)
        cmd_startworker "$@"
        ;;
    *)
        echo "Error: Unknown command '$COMMAND'" >&2
        usage
        ;;
esac