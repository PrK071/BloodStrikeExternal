# PowerShell / native/build.ps1 / PowerShell 7 / Windows x64 with Zig 0.14.1
param([string]$Zig = 'zig', [string]$Output = "$PSScriptRoot\Aeon.exe")
$ErrorActionPreference = 'Stop'
& $Zig c++ "$PSScriptRoot\rook.cpp" -target x86_64-windows-gnu -std=c++20 -O2 -municode '-Wl,--subsystem,windows' -luser32 -lgdi32 -lshell32 -ladvapi32 -lbcrypt -lcomctl32 -o $Output
if ($LASTEXITCODE -ne 0) { throw "Compilation failed ($LASTEXITCODE)" }
$test = Start-Process -FilePath $Output -ArgumentList '--self-test' -PassThru -Wait -WindowStyle Hidden
if ($test.ExitCode -ne 0) { throw 'Native self-test failed' }
Get-Item -LiteralPath $Output
