#!/usr/bin/env bash

# Exit immediately if a command exits with a non-zero status
set -euo pipefail

: "${BUILDERNAME:=dumb-builder}"
: "${DUMB_WORKER_DIR:=$HOME/dumb-worker}" 

SCRIPT_NAME=$(basename $0)

LONG_NAME="${SCRIPT_NAME//.sh/}"

if [[ $# -ge 1 ]]; then
    if [ -v 1 ]; then
        # Remove double 'minus'es at beginning
        LONG_NAME="$LONG_NAME-${1/--/}"
    fi
    if [ -v 2 ]; then
        LONG_NAME="$LONG_NAME-${2/--/}"
    fi
    if [ -v 3 ]; then
        LONG_NAME="$LONG_NAME-${3/--/}"
    fi
    if [ -v 4 ]; then
        LONG_NAME="$LONG_NAME-${4/--/}"
    fi
    # Remove dots prefix
    LONG_NAME="${LONG_NAME//-./}"
    LONG_NAME="${LONG_NAME//./}"
    LONG_NAME="${LONG_NAME//--/-}"
    LONG_NAME="${LONG_NAME//--/-}"
fi

cat "$DUMB_WORKER_DIR/logs/$BUILDERNAME/$LONG_NAME.log"
