<#
.SYNOPSIS
    Build bo cai dat nhe dist\AutoGuardian-Setup.exe va file dist\manifest.json cho GitHub Release.

.DESCRIPTION
    AutoGuardian-Setup.exe (vai MB) tu phat hien GPU NVIDIA va tai goi ung dung phu hop (GPU hoac CPU)
    tu GitHub Release. manifest.json liet ke cac goi (URL, kich thuoc, SHA-256).

    Can chay build_exe.ps1 va build_exe.ps1 -Cuda truoc de co cac goi trong dist\.
    -SkipManifest: chi build exe (CI tao manifest sau khi da ky so va dong goi).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build_launcher.ps1 -AppVersion 1.1.0 -PackageTag v1.1.0
#>
param(
    [Parameter(Mandatory = $true)][string]$AppVersion,
    [string]$PackageTag,
    [switch]$SkipManifest
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-Checked {
    $Cmd = [string[]]$args
    Write-Host ">> $($Cmd -join ' ')" -ForegroundColor DarkGray
    $ErrorActionPreference = "Continue"
    & $Cmd[0] $Cmd[1..($Cmd.Length - 1)]
    $ErrorActionPreference = "Stop"
    if ($LASTEXITCODE -ne 0) { throw "Lenh that bai (exit $LASTEXITCODE): $($Cmd -join ' ')" }
}

if (-not $SkipManifest -and -not $PackageTag) { throw "Can -PackageTag (hoac dung -SkipManifest)" }

$venv = ".venv-build"
$py = Join-Path $venv "Scripts\python.exe"
if (-not (Test-Path $py)) {
    Invoke-Checked python -m venv $venv
    Invoke-Checked $py -m pip install "pyinstaller==6.22.3"
}

Write-Host "[1/2] Build AutoGuardian-Setup.exe (phien ban $AppVersion)" -ForegroundColor Cyan
New-Item -ItemType Directory -Force build\launcher | Out-Null
Invoke-Checked $py tools\make_version_info.py $AppVersion AutoGuardian-Setup.exe "AutoGuardian - Bo cai dat" build\launcher\version_info.txt
Invoke-Checked $py -m PyInstaller launcher\autoguardian_launcher.py `
    --name AutoGuardian-Setup `
    --distpath dist --workpath build\launcher `
    --version-file build\launcher\version_info.txt `
    --noconfirm --clean --windowed --onefile

if (-not $SkipManifest) {
    Write-Host "[2/2] Tao manifest.json (goi tai tu release $PackageTag)" -ForegroundColor Cyan
    Invoke-Checked $py tools\make_manifest.py --app-version $AppVersion --tag $PackageTag --out dist\manifest.json
}

$size = [math]::Round((Get-Item dist\AutoGuardian-Setup.exe).Length / 1MB, 1)
Write-Host "Xong: dist\AutoGuardian-Setup.exe ($size MB)" -ForegroundColor Green
