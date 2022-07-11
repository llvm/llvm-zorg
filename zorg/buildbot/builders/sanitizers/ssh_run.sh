#!/bin/bash -eu
#
# Runs the given command over ssh using SSH_CONTROL_SOCKET.
#

function run_in_qemu {
  ssh -S "${SSH_CONTROL_SOCKET}" root@localhost "${@}"
}

# Run binary in QEMU.
ENV="HWASAN_OPTIONS=\"${HWASAN_OPTIONS:-}\" PATH=\"${PATH:-}\""
run_in_qemu "cd $(pwd) && ${ENV} $@"
