# PowerShell | tools/rea.ps1 | PowerShell 7/Node 24 | workspace-local REA CLI and static-analysis providers.
param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ReaArguments)
$ErrorActionPreference = 'Stop'
$reaToolRoot = $PSScriptRoot
$reaNode = 'C:\Users\luiz\.cache\codex-runtimes\codex-primary-runtime\dependencies\node\bin\node.exe'
$reaEntry = Join-Path $reaToolRoot 'rea-runtime\node_modules\rea-agents\scripts\rea.mjs'
if (-not (Test-Path -LiteralPath $reaNode)) { $reaNode = (Get-Command node -ErrorAction Stop).Source }
if (-not (Test-Path -LiteralPath $reaEntry)) { throw 'The workspace REA CLI is missing.' }
$reaPreviousGhidra = $env:GHIDRA_INSTALL_DIR
$reaPreviousJava = $env:JAVA_HOME
try {
    $env:GHIDRA_INSTALL_DIR = Join-Path $reaToolRoot 'providers\ghidra12.1.4\ghidra_12.1.4_PUBLIC'
    $env:JAVA_HOME = Join-Path $reaToolRoot 'providers\jdk21\jdk-21.0.9+10'
    & $reaNode $reaEntry @ReaArguments
    exit $LASTEXITCODE
} finally {
    $env:GHIDRA_INSTALL_DIR = $reaPreviousGhidra
    $env:JAVA_HOME = $reaPreviousJava
}
