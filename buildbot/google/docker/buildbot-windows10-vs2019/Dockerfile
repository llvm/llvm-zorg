# escape=`
FROM gcr.io/sanitizer-bots/windows-base-vscode2019:8

ENV WORKER_NAME=windows10-vs2019

# copy script to start the agent
COPY run.ps1 .
COPY fix_buildbot_tac_paths.py .

# Set location for sccache cache
ENV SCCACHE_DIR="C:\volumes\sccache"

# Set the maximum sccache local cache size
ENV SCCACHE_CACHE_SIZE="10G"

# Move buildbot work dir to a volume to avoid of disc issues
VOLUME C:\volumes\buildbot

# Configure 32bit tools ("x86") instead of 64bit ("amd64")
CMD ["powershell.exe", "-NoLogo", "-ExecutionPolicy", "Bypass", `
     "c:\\buildbot\\run.ps1"]
