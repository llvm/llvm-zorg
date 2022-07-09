#!/bin/bash -eu
#
# Runs the given command over ssh using SSH_CONTROL_SOCKET.
#

: ${HWASAN_OPTIONS:=""}

function copy_to_qemu {
  local local_file="${1}"
  local qemu_dir="${2}"

  scp -o "ControlPath=${SSH_CONTROL_SOCKET}" \
    "${local_file}" "root@localhost:${qemu_dir}/"
}

function run_in_qemu {
  echo "Running command in QEMU: ${@}" >&2
  ssh -S "${SSH_CONTROL_SOCKET}" root@localhost "${@}"
}

if [[ -f ${1} ]] ; then
  readonly BINARY_PATH="$(readlink -f ${1})"
  readonly BINARY_DIR="$(dirname ${BINARY_PATH})"
  # Copy binary to QEMU.
  run_in_qemu "mkdir -p ${BINARY_DIR}"
  copy_to_qemu "${BINARY_PATH}" "${BINARY_DIR}"
fi

# Run binary in QEMU.
ENV="HWASAN_OPTIONS=\"${HWASAN_OPTIONS}\""
run_in_qemu "${ENV} $@"
