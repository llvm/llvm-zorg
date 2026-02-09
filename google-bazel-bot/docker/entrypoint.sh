#!/usr/bin/env bash

set -eu
set -o pipefail

USER=buildkite-agent
P="${BUILDKITE_BUILD_PATH:=/var/lib/buildkite-agent}"
mkdir -p "$P"
chown -R ${USER}:${USER} "$P"

export CCACHE_DIR="${P}"/ccache
export CCACHE_MAXSIZE=20G
mkdir -p "${CCACHE_DIR}"
chown -R ${USER}:${USER} "${CCACHE_DIR}"

export SCCACHE_DIR="$BUILDKITE_BUILD_PATH/sccache"
export SCCACHE_IDLE_TIMEOUT="0"
rm -rf "$SCCACHE_DIR"
mkdir -p "${SCCACHE_DIR}"
chown -R ${USER}:${USER} "${SCCACHE_DIR}"
chmod oug+rw "${SCCACHE_DIR}"
gosu "$USER" bash -c 'SCCACHE_DIR="${SCCACHE_DIR}" SCCACHE_IDLE_TIMEOUT=0 SCCACHE_CACHE_SIZE=20G sccache --start-server'

# /mnt/ssh should contain known_hosts, id_rsa and id_rsa.pub .
mkdir -p /var/lib/buildkite-agent/.ssh
if [[ -d /mnt/ssh ]]; then
  cp /mnt/ssh/* /var/lib/buildkite-agent/.ssh || echo "no "
  chmod 700 /var/lib/buildkite-agent/.ssh
  chmod 600 /var/lib/buildkite-agent/.ssh/*
  chown -R buildkite-agent:buildkite-agent /var/lib/buildkite-agent/.ssh/
else
  echo "/mnt/ssh is not mounted"
fi

# Run with tini to correctly pass exit codes.
exec /usr/bin/tini -g -- "$@"
