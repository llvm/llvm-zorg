# Stop the script on the first error
$ErrorActionPreference = "Stop"

# Read password from file
$WORKER_PASSWORD=Get-Content "C:\volumes\secrets\token"

# chdir to the volume storing the temporary data
# This is a mounted volume
Set-Location c:\volumes\buildbot

# Write host and admin information
# configure powershell output to use UTF-8, otherwiese buildbot can't read the file
mkdir "$env:WORKER_NAME\info\"
$HOST_FILE="$env:WORKER_NAME\info\host"
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
Write-Output "Windows version: $(cmd /c ver)" > $HOST_FILE
Write-Output "VCTools version: $env:VCToolsVersion" >> $HOST_FILE
Write-Output "Cores          : $((Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors)" >> $HOST_FILE
Write-Output "RAM            : $([int][Math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1073741824)) GB" >> $HOST_FILE
Write-Output "Christian Kühnel <kuhnel@google.com>" > "$env:WORKER_NAME\info\admin"

# create the worker
Write-Output "creating worker..."
buildslave create-slave --keepalive=200 "$env:WORKER_NAME" `
  "lab.llvm.org:9994" "$env:WORKER_NAME" "$WORKER_PASSWORD"

# Note: Powershell does NOT exit on non-zero return codes, so we need to check manually.
if ($LASTEXITCODE -ne 0) { throw "Exit code is $LASTEXITCODE" }

# start the daemon, as this does not print and logs to std out, run it in the background
Write-Output "starting worker..."
cmd /c Start /B buildslave start "$env:WORKER_NAME"

# Wait a bit until the logfile exists
Start-Sleep -s 5

# To keep the container running and produce log outputs: dump the worker
# log to stdout, this is the windows equivalent of `tail -f`
Get-Content -Path "$env:WORKER_NAME\twistd.log" -Wait
