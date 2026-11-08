#  DeepSeek Whale Girl cursor scheme - per-user installer (no admin needed)
#  Usage:
#     powershell -ExecutionPolicy Bypass -File install.ps1 -Scheme Moe
#     powershell -ExecutionPolicy Bypass -File install.ps1 -Scheme MoeChan
#     powershell -ExecutionPolicy Bypass -File install.ps1 -Restore
param(
    [ValidateSet('Moe', 'MoeChan', 'Aero')]
    [string]$Scheme = 'Moe',
    [switch]$Restore
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = $here
$backup = Join-Path $root 'backup_cursors.json'
$key = 'HKCU:\Control Panel\Cursors'
$roles = @('Arrow', 'Help', 'AppStarting', 'Wait', 'Crosshair', 'IBeam', 'NWPen', 'No',
           'SizeNS', 'SizeWE', 'SizeNWSE', 'SizeNESW', 'SizeAll', 'UpArrow', 'Hand', 'Pin')
$files = @{
    Arrow = 'arrow.cur'; Help = 'help.cur'; AppStarting = 'appstarting.ani'
    Wait = 'busy.ani'; Crosshair = 'cross.cur'; IBeam = 'ibeam.cur'; NWPen = 'pen.cur'
    No = 'no.cur'; SizeNS = 'sizens.cur'; SizeWE = 'sizewe.cur'
    SizeNWSE = 'sizenwse.cur'; SizeNESW = 'sizenesw.cur'; SizeAll = 'sizeall.cur'
    UpArrow = 'uparrow.cur'; Hand = 'hand.cur'; Pin = 'pin.cur'
}
# stock Windows 10/11 scheme; empty string means "delete the value, use the system default"
$aero = @{
    Arrow = '%SystemRoot%\cursors\aero_arrow.cur'
    Help = '%SystemRoot%\cursors\aero_helpsel.cur'
    AppStarting = '%SystemRoot%\cursors\aero_working.ani'
    Wait = '%SystemRoot%\cursors\aero_busy.ani'
    Crosshair = ''; IBeam = ''
    NWPen = '%SystemRoot%\cursors\aero_pen.cur'
    No = '%SystemRoot%\cursors\aero_unavail.cur'
    SizeNS = '%SystemRoot%\cursors\aero_ns.cur'
    SizeWE = '%SystemRoot%\cursors\aero_ew.cur'
    SizeNWSE = '%SystemRoot%\cursors\aero_nwse.cur'
    SizeNESW = '%SystemRoot%\cursors\aero_nesw.cur'
    SizeAll = '%SystemRoot%\cursors\aero_move.cur'
    UpArrow = '%SystemRoot%\cursors\aero_up.cur'
    Hand = '%SystemRoot%\cursors\aero_link.cur'
    Pin = '%SystemRoot%\cursors\aero_pin.cur'
}
$ours = @('DeepSeek Moe', 'DeepSeek Moe Chan')

function Native-Refresh {
    try {
        Add-Type -Namespace Win -Name Cur -MemberDefinition @'
[System.Runtime.InteropServices.DllImport("user32.dll", SetLastError=true)]
public static extern bool SystemParametersInfo(uint a, uint b, System.IntPtr c, uint d);
'@ -ErrorAction Stop
        [Win.Cur]::SystemParametersInfo(0x0057, 0, [IntPtr]::Zero, 3) | Out-Null
    } catch {
        Start-Process -FilePath 'rundll32.exe' -ArgumentList 'user32.dll,UpdatePerUserSystemParameters' -NoNewWindow -Wait
    }
}

function Set-Cur([string]$name, [string]$value) {
    if ([string]::IsNullOrWhiteSpace($value)) {
        Remove-ItemProperty -Path $key -Name $name -ErrorAction SilentlyContinue
        return
    }
    $type = 'String'
    if ($value.Contains('%')) { $type = 'ExpandString' }
    New-ItemProperty -Path $key -Name $name -Value $value -PropertyType $type -Force | Out-Null
}

# ------------------------------------------------------------------ restore ---
if ($Restore) { $Scheme = 'Aero' }

if ($Scheme -eq 'Aero') {
    if (-not (Test-Path 'C:\Windows\Cursors\aero_arrow.cur')) {
        Write-Host 'Stock Aero cursors not found; falling back to saved backup.' -ForegroundColor Yellow
        if (-not (Test-Path $backup)) { Write-Host 'No backup either. Aborting.' -ForegroundColor Red; exit 1 }
        $b = Get-Content -Raw -Encoding UTF8 $backup | ConvertFrom-Json
        foreach ($r in $roles) { Set-Cur $r $b.values.($r) }
        if ($b.name) { Set-ItemProperty -Path $key -Name '(default)' -Value $b.name }
    } else {
        foreach ($r in $roles) { Set-Cur $r $aero[$r] }
        Set-ItemProperty -Path $key -Name '(default)' -Value 'Windows Aero'
    }
    Native-Refresh
    Write-Host ''
    Write-Host 'Restored: Windows Aero (stock) cursors.' -ForegroundColor Green
    Write-Host 'If a window still shows the old pointer, sign out and back in.'
    exit 0
}

# ------------------------------------------------------------------- backup ---
# Only snapshot the current state when it is NOT already one of our schemes,
# otherwise the "backup" would just point at our own files.
$curName = (Get-ItemProperty -Path $key -Name '(default)' -ErrorAction SilentlyContinue).'(default)'
$polluted = ($curName -in $ours) -or ((Test-Path $backup) -and ((Get-Content -Raw -Encoding UTF8 $backup | ConvertFrom-Json).name -in $ours))

if ($polluted) {
    $snap = @{}
    foreach ($r in $roles) { $snap[$r] = $aero[$r] }
    @{ values = $snap; name = 'Windows Aero' } | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $backup
    Write-Host "Backup was stale; rewrote it as the stock Aero scheme." -ForegroundColor Yellow
} elseif (-not (Test-Path $backup)) {
    $snap = @{}
    foreach ($r in $roles) {
        $snap[$r] = (Get-ItemProperty -Path $key -Name $r -ErrorAction SilentlyContinue).($r)
    }
    @{ values = $snap; name = $curName } | ConvertTo-Json -Depth 4 | Set-Content -Encoding UTF8 $backup
}

# ----------------------------------------------------------------- install ----
$sub = if ($Scheme -eq 'MoeChan') { 'cursors_moe' } else { 'cursors' }
$srcDir = Join-Path $root $sub
if (-not (Test-Path $srcDir)) {
    Write-Host "Cursor folder not found: $srcDir" -ForegroundColor Red
    Write-Host "Folders next to this script:" -ForegroundColor Yellow
    Get-ChildItem -Directory -Path $root | Select-Object -ExpandProperty Name | ForEach-Object { Write-Host "  $_" }
    exit 1
}

$dest = Join-Path $env:LOCALAPPDATA 'DeepSeekMoe\Cursors'
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item -Path (Join-Path $srcDir '*') -Destination $dest -Force

$schemeName = if ($Scheme -eq 'MoeChan') { 'DeepSeek Moe Chan' } else { 'DeepSeek Moe' }
$pathList = @()
foreach ($r in $roles) {
    $f = Join-Path $dest $files[$r]
    Set-Cur $r $f
    $pathList += $f
}
Set-ItemProperty -Path $key -Name '(default)' -Value $schemeName

$schemesKey = 'HKCU:\Control Panel\Cursors\Schemes'
if (-not (Test-Path $schemesKey)) { New-Item -Path $schemesKey -Force | Out-Null }
Set-ItemProperty -Path $schemesKey -Name $schemeName -Value ($pathList -join ',')

Native-Refresh

Write-Host ""
Write-Host "Installed: $schemeName" -ForegroundColor Green
Write-Host "Files    : $dest"
Write-Host "Backup   : $backup"
Write-Host "Revert   : run this script with -Restore"
Write-Host "It is also selectable in Settings > Mouse > Additional mouse settings > Pointers."