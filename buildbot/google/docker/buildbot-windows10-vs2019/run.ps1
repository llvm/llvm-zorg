# Stop the script on the first error
$ErrorActionPreference = "Stop"

# Read password from file
$WORKER_PASSWORD=Get-Content "C:\volumes\secrets\token"

#Create short drive alias "Q:" for worker dir, to keep path lengths <260 
SUBST Q: C:\volumes\buildbot
Get-PSDrive

# chdir to the volume storing the temporary data
# This is a mounted volume
Set-Location Q:\

# Write host and admin information
# delete old folder if it exists
# configure powershell output to use UTF-8, otherwiese buildbot can't read the file
if ( Test-Path -Path 'info\' -PathType Container ) { 
  Remove-Item -Recurse -Force info 
}
mkdir "info\"
$HOST_FILE="info\host"
$PSDefaultParameterValues['Out-File:Encoding'] = 'utf8'
Write-Output "Windows version: $(cmd /c ver)" > $HOST_FILE
Write-Output "VCTools version: $env:VCToolsVersion" >> $HOST_FILE
Write-Output "Cores          : $((Get-CimInstance Win32_ComputerSystem).NumberOfLogicalProcessors)" >> $HOST_FILE
Write-Output "RAM            : $([int][Math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1073741824)) GB" >> $HOST_FILE
Write-Output "Christian Kühnel <kuhnel@google.com>" > "info\admin"

# create the worker
Write-Output "creating worker..."
buildslave create-slave --keepalive=200 Q: `
  "lab.llvm.org:9994" "$env:WORKER_NAME" "$WORKER_PASSWORD"
# Note: Powershell does NOT exit on non-zero return codes, so we need to check manually.
if ($LASTEXITCODE -ne 0) { throw "Exit code of 'buildslave create' is $LASTEXITCODE" }

# Replace backward slashes with forward slashes on buildbot.tac
# Otherwise Cmake will go into infinite re-configuration loops
python C:\buildbot\fix_buildbot_tac_paths.py buildbot.tac
if ($LASTEXITCODE -ne 0) { throw "Exit code of 'fix_buildbot_tac_paths' is $LASTEXITCODE" }

# start the daemon, as this does not print and logs to std out, run it in the background
Write-Output "starting worker..."
cmd /c Start /B buildslave start Q:

# Wait a bit until the logfile exists
Start-Sleep -s 5

# To keep the container running and produce log outputs: dump the worker
# log to stdout, this is the windows equivalent of `tail -f`
Get-Content -Path "Q:\twistd.log" -Wait
