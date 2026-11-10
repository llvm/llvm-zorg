#!/usr/bin/env python3
"""Run every Mach-O executable in the given directories once.

Usage: prescan_binaries.py DIR [DIR...]
"""

import os
import platform
import subprocess
import sys
import tempfile
import time

# Mach-O thin (32/64-bit) and universal binary magic numbers in both byte orders.
MACHO_MAGICS = {
    bytes.fromhex(m)
    for m in (
        "feedface",
        "cefaedfe",
        "feedfacf",
        "cffaedfe",
        "cafebabe",
        "bebafeca",
    )
}

TIMEOUT_SECONDS = 600

# Binaries whose file name contains any of these strings are not launched.
EXCLUDED_BINARIES = [
    # Doesn't do arg parsing and would run for a long time.
    "llvm-PerfectShuffle",
]


def is_macho_executable(path):
    if os.path.islink(path) or not os.path.isfile(path):
        return False
    if not os.access(path, os.X_OK):
        return False
    try:
        with open(path, "rb") as f:
            return f.read(4) in MACHO_MAGICS
    except OSError:
        return False


def find_binaries(dirs):
    binaries = []
    for d in dirs:
        if not os.path.isdir(d):
            print("Skipping non-existent directory: {}".format(d))
            continue
        for name in sorted(os.listdir(d)):
            if any(excluded in name for excluded in EXCLUDED_BINARIES):
                print("Skipping excluded binary: {}".format(name))
                continue
            path = os.path.join(d, name)
            if is_macho_executable(path):
                binaries.append(os.path.abspath(path))
    return binaries


def run_binary(path, cwd):
    start = time.time()
    try:
        proc = subprocess.run(
            [path, "--version"],
            cwd=cwd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS,
        )
        status = "exit code {}".format(proc.returncode)
    except subprocess.TimeoutExpired:
        status = "timed out"
    except OSError as e:
        status = "failed to launch: {}".format(e)
    return path, status, time.time() - start


def main():
    if platform.system() != "Darwin":
        print("Not running on macOS, nothing to do.")
        return 0

    binaries = find_binaries(sys.argv[1:])
    print("Pre-scanning {} binaries...".format(len(binaries)))

    # Run in a scratch directory so binaries that create files on startup
    # don't pollute the build directory.
    with tempfile.TemporaryDirectory() as cwd:
        # Run sequentially as the malware scanner only scans one binary at a
        # time anyway.
        for binary in binaries:
            path, status, duration = run_binary(binary, cwd)
            size_mib = os.path.getsize(path) / (1024 * 1024)
            print("  {:6.1f}s  {:8.1f} MiB  {} ({})".format(
                duration, size_mib, path, status))
            sys.stdout.flush()
    # Never fail the build because of this step.
    return 0


if __name__ == "__main__":
    sys.exit(main())
