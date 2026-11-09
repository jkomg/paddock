# Native PowerShell entry point. Requires Python 3.11+ on PATH.
$ErrorActionPreference = 'Stop'
& python "$PSScriptRoot/install.py" @args
exit $LASTEXITCODE
