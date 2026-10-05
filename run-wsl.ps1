param(
    [ValidateRange(1024, 65535)]
    [int]$Port = 8001
)
$ErrorActionPreference = 'Stop'
$LinuxRepo = (& wsl.exe -d Ubuntu --exec wslpath -a $PSScriptRoot).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve repository path in Ubuntu.' }
& wsl.exe -d Ubuntu -u md_soriful_islam -- sh "$LinuxRepo/run-wsl.sh" $Port
if ($LASTEXITCODE -ne 0) { throw "WSL API exited with code $LASTEXITCODE" }
