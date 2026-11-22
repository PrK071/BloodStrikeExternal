# check_ntoskrnl_export.ps1 - read-only PE export lookup, no dependencies.
#
# Used by the VM gate G1: proves whether the guest kernel exports a symbol.
# Does not need elevation, does not load anything, does not write files.
#
# Exit codes: 0 = export found, 2 = export not found, 3 = parse/setup error.
#
# Usage:
#   powershell -NoProfile -ExecutionPolicy Bypass -File check_ntoskrnl_export.ps1
#   ... -Name IoCreateDeviceSecure
#   ... -Path D:\image\Windows\System32\ntoskrnl.exe

param(
    [string]$Path = "$env:SystemRoot\System32\ntoskrnl.exe",
    [string]$Name = "IoCreateDeviceSecure"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $Path)) {
    Write-Output "ERROR: not found: $Path"
    exit 3
}

try {
    $bytes = [IO.File]::ReadAllBytes($Path)
    function U16($o) { [BitConverter]::ToUInt16($bytes, $o) }
    function U32($o) { [BitConverter]::ToUInt32($bytes, $o) }

    $pe = U32 0x3C
    if ($bytes[$pe] -ne 0x50 -or $bytes[$pe + 1] -ne 0x45) { throw "not a PE file" }

    $numSections = U16 ($pe + 6)
    $optSize     = U16 ($pe + 20)
    $opt         = $pe + 24
    if ((U16 $opt) -ne 0x20B) { throw "not PE32+ (x64)" }

    $expRva  = U32 ($opt + 112)
    $expSize = U32 ($opt + 116)
    if (-not $expRva) { throw "image has no export directory" }

    $secBase = $opt + $optSize
    $sections = @()
    for ($i = 0; $i -lt $numSections; $i++) {
        $o = $secBase + $i * 40
        $sections += [pscustomobject]@{
            VA   = (U32 ($o + 12)); VS = (U32 ($o + 8))
            Raw  = (U32 ($o + 20)); RS = (U32 ($o + 16))
        }
    }

    function RvaToOffset([uint32]$rva) {
        foreach ($s in $sections) {
            $end = $s.VA + [Math]::Max($s.VS, $s.RS)
            if ($rva -ge $s.VA -and $rva -lt $end) { return ($s.Raw + ($rva - $s.VA)) }
        }
        return -1
    }

    $expOff   = RvaToOffset $expRva
    $nNames   = U32 ($expOff + 24)
    $namesOff = RvaToOffset (U32 ($expOff + 32))
    $ordsOff  = RvaToOffset (U32 ($expOff + 36))
    $funcsOff = RvaToOffset (U32 ($expOff + 28))

    $found = $null
    for ($i = 0; $i -lt $nNames; $i++) {
        $p = RvaToOffset (U32 ($namesOff + $i * 4))
        $s = ""
        while ($p -ge 0 -and $p -lt $bytes.Length -and $bytes[$p] -ne 0) {
            $s += [char]$bytes[$p]; $p++
        }
        if ($s -ceq $Name) {
            $ord = U16 ($ordsOff + $i * 2)
            $found = U32 ($funcsOff + $ord * 4)
            break
        }
    }
} catch {
    Write-Output "ERROR: $($_.Exception.Message)"
    exit 3
}

$ver = (Get-Item $Path).VersionInfo.FileVersion
$sha = (Get-FileHash $Path -Algorithm SHA256).Hash
$cv  = Get-ItemProperty 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion' -ErrorAction SilentlyContinue
$build = if ($cv) { "$($cv.CurrentBuild).$($cv.UBR) $($cv.ProductName) $($cv.DisplayVersion)" } else { "unknown" }

Write-Output "kernel   : $Path"
Write-Output "build    : $build"
Write-Output "version  : $ver"
Write-Output "sha256   : $sha"

if ($null -ne $found) {
    Write-Output ("export   : {0} RVA=0x{1:X}" -f $Name, $found)
    exit 0
}

Write-Output "export   : $Name NOT FOUND"
exit 2
