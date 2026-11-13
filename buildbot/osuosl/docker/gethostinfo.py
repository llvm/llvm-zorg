#!/usr/bin/env python3
"""Print or write a concise description for a Buildbot worker's Host row."""

import configparser
import os
import platform
import re
import shutil
import subprocess
import sys

__version__ = "1.0.0"

from configparser import ConfigParser, ExtendedInterpolation
options = ConfigParser(
    interpolation = configparser.ExtendedInterpolation(),
    empty_lines_in_values = False,
    allow_no_value = True,
)

def command_output(args, timeout=5):
    try:
        result = subprocess.run(
            args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, timeout=timeout, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return result.stdout.strip()


def tool_version(name, args, pattern):
    extra_paths = options.get("DEFAULT", "extra_paths", fallback="")
    if extra_paths:
        extra_paths = [line.strip() for line in extra_paths.splitlines() if line.strip()]
    custom_path = os.pathsep.join((extra_paths or []) + [os.environ.get("PATH", "")])

    executable = shutil.which(name, path=custom_path)
    if not executable:
        return None
    output = command_output([executable, *args])
    if not output:
        return None
    if pattern is None:
        return output
    match = re.search(pattern, output)
    if match:
        return ".".join(filter(None, match.groups()))
    return None

def memory_description():
    try:
        import psutil

        mem_info = psutil.virtual_memory()
        gib = mem_info.total / 1024**3

        return f"{gib:.0f} GiB"
    except ImportError:
        psutil = None   
    return None


def describe_host():
    parts = []

    if options.getboolean("DEFAULT", "show_os", fallback=True):
        os_name = options.get("DEFAULT", "os", fallback="")
        if not os_name:
            if platform.system() == "Linux" and os.path.exists("/etc/os-release"):
                os_release = ConfigParser()
                with open("/etc/os-release") as f:
                    os_release.read_string("[os-release]\n" + f.read())
                os_name = os_release.get("os-release", "PRETTY_NAME", fallback="")
                if not os_name:
                    os_name = os_release.get("os-release", "NAME", fallback="Unknown")
                os_name = os_name.strip('"')
            else:
                os_name = " ".join(filter(None, (platform.system(), platform.release()))) + "/" + platform.machine()
        parts.append(f"OS: {os_name}")

    if options.getboolean("DEFAULT", "show_cpu", fallback=True):
        cpu = options.get("DEFAULT", "cpu", fallback = "")
        cpu_str = "CPU: "
        if not cpu:
            cpu = platform.processor() or "Unknown"
            cpu_str += re.sub(r'\s+', ' ', cpu).strip()
            if os.cpu_count():
                cpu_str += f" (cores: {os.cpu_count()})"
        else:
            cpu_str += cpu
        parts.append(cpu_str)

    if options.getboolean("DEFAULT", "show_memory", fallback=True):
        memory = options.get("DEFAULT", "memory", fallback="") or memory_description()
        if memory:
            parts.append(f"RAM: {memory}")

    if options.getboolean("DEFAULT", "show_tools", fallback=True):
        check_tools = list(filter(None, [t.strip() for t in options.get("DEFAULT", "tools", fallback="").split(",")]))

        tools = (
            ("cmake", ["--version"], "CMake", r"cmake version (\d+)\.(\d+)(?:\.(\d+))?"),
            ("ninja", ["--version"], "Ninja", r"(\d+)\.(\d+)(?:\.(\d+))?"),
            ("make", ["--version"], "Make", r"GNU Make (\d+)\.(\d+)(?:\.(\d+))?"),
            ("python3", ["--version"], "Python", r"Python (\d+)\.(\d+)(?:\.(\d+))?"),
            ("gcc", ["--version"], "GCC", r"gcc \(.+\) (\d+)\.(\d+)(?:\.(\d+))?"),
            ("clang", ["--version"], "Clang", r"^.clang version (\d+)\.(\d+)(?:\.(\d+))?"),
            ("ld", ["--version"], "LD", r"GNU ld \(.+\) (\d+)\.(\d+)(?:\.(\d+))?"),
            ("ld.lld", ["--version"], "LLD", r"^.lld version (\d+)\.(\d+)(?:\.(\d+))?"),
            ("vswhere.exe", ["-latest", "-property", "InstallationVersion"], "Visual Studio", None),
            ("nvcc", ["--version"], "CUDA", r"Cuda compilation tools, release .+, V(\d+)\.(\d+)(?:\.(\d+))?"),
        )
        parts.extend(f"{display_name}: {version}" for name, args, display_name, pattern in tools
                     if (not check_tools or display_name in check_tools) and (version := tool_version(name, args, pattern)))
    return "; ".join(part for part in parts if part)


def main():
    filename = os.path.splitext(os.path.basename(__file__))[0]
    ini_file = os.path.join(os.path.dirname(__file__), filename + ".ini")
    if os.path.exists(ini_file):
        print(f"Using INI file: {ini_file}", file=sys.stderr)
        options.read(ini_file)

    description = []
    description.append(options.get("DEFAULT", "description", fallback=""))
    description.append(describe_host())
    description = "; ".join(list(filter(None, description)))
    if len(sys.argv) > 1:
        with open(sys.argv[1], "w", encoding="utf-8") as stream:
            stream.write(description + "\n")
    else:
        print(description)


if __name__ == "__main__":
    main()
    exit(0)