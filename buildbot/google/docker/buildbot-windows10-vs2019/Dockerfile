# escape=`
FROM gcr.io/sanitizer-bots/windows-base-vscode2019:7

ENV WORKER_NAME=windows10-vs2019

# copy admin information
RUN md %WORKER_NAME%\info
COPY admin ${WORKER_NAME}\info

# copy script to start the agent
COPY run.ps1 .

# Set location for sccache cache
ENV SCCACHE_DIR="C:\volumes\sccache"

# Set the maximum sccache local cache size
ENV SCCACHE_CACHE_SIZE="5G"

# Configure 32bit tools ("x86") instead of 64bit ("amd64")
ENTRYPOINT ["C:\\BuildTools\\Common7\\Tools\\VsDevCmd.bat", "-arch=x86", `
    "-host_arch=amd64", "&&", "powershell.exe", "-NoLogo", `
    "-ExecutionPolicy", "Bypass"]

CMD ["c:\\buildbot\\run.ps1"]
