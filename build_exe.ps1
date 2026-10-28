<#
.SYNOPSIS
    Dong goi AutoGuardian thanh ung dung Windows: dist\<cpu|cuda>\AutoGuardian\AutoGuardian.exe

.DESCRIPTION
    Mac dinh build voi PyTorch ban CPU: chay duoc tren moi may Windows x64, co hoac khong co GPU.
    -Cuda: build voi PyTorch CUDA (nang hon nhieu, ~4 GB) de tan dung GPU NVIDIA;
           van tu dong chay bang CPU tren may khong co GPU.

    Ket qua: thu muc dist\cpu\AutoGuardian hoac dist\cuda\AutoGuardian (copy nguyen thu muc
    sang may khac la chay duoc) va file nen dist\AutoGuardian-win64[-cuda].zip
    (tu chia thanh .zip.001, .zip.002... neu lon hon 1.9 GB).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File build_exe.ps1
    powershell -ExecutionPolicy Bypass -File build_exe.ps1 -Cuda
#>
param(
    [switch]$Cuda,
    [switch]$NoZip
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Invoke-Checked {
    # Dung $args (khong khai bao param) de cac doi so nhu "-c", "-m" duoc chuyen nguyen ven cho lenh
    $Cmd = [string[]]$args
    Write-Host ">> $($Cmd -join ' ')" -ForegroundColor DarkGray
    # Canh bao cua pip/PyInstaller ghi ra stderr khong phai la loi: chi xet exit code
    $ErrorActionPreference = "Continue"
    & $Cmd[0] $Cmd[1..($Cmd.Length - 1)]
    $ErrorActionPreference = "Stop"
    if ($LASTEXITCODE -ne 0) { throw "Lenh that bai (exit $LASTEXITCODE): $($Cmd -join ' ')" }
}

if ($Cuda) {
    $venv = ".venv-build-cuda"
    $torchIndex = "https://download.pytorch.org/whl/cu124"
    $zipName = "AutoGuardian-win64-cuda.zip"
    $distRoot = "dist\cuda"
} else {
    $venv = ".venv-build"
    $torchIndex = "https://download.pytorch.org/whl/cpu"
    $zipName = "AutoGuardian-win64.zip"
    $distRoot = "dist\cpu"
}
$py = Join-Path $venv "Scripts\python.exe"

# 1. Moi truong build rieng (khong anh huong .venv dang dung de phat trien)
Write-Host "[1/5] Chuan bi moi truong build: $venv" -ForegroundColor Cyan
if (-not (Test-Path $py)) { Invoke-Checked python -m venv $venv }
Invoke-Checked $py -m pip install --upgrade pip
Invoke-Checked $py -m pip install "torch==2.6.0" "torchvision==0.21.0" --index-url $torchIndex
Invoke-Checked $py -m pip install -r requirements.txt "pyinstaller==6.22.3"
Invoke-Checked $py -m pip install --no-deps -r requirements-nodeps.txt

# PyQt5 kem VC++ runtime cu (14.26). onnxruntime moi (build bang VS 17.10+) bi crash (0xC0000005)
# neu runtime cu duoc nap truoc -> thay bang ban moi hon cua he thong, ap dung cho ca file exe.
function Get-DllVersion($path) {
    $v = (Get-Item $path).VersionInfo
    return New-Object Version $v.FileMajorPart, $v.FileMinorPart, $v.FileBuildPart, $v.FilePrivatePart
}
$qtBin = Join-Path $venv "Lib\site-packages\PyQt5\Qt5\bin"
foreach ($dll in "msvcp140.dll", "msvcp140_1.dll", "msvcp140_2.dll", "vcruntime140.dll", "vcruntime140_1.dll") {
    $sysDll = Join-Path $env:SystemRoot "System32\$dll"
    $qtDll = Join-Path $qtBin $dll
    if ((Test-Path $sysDll) -and (Test-Path $qtDll) -and ((Get-DllVersion $sysDll) -gt (Get-DllVersion $qtDll))) {
        Copy-Item $sysDll $qtDll -Force
        Write-Host "   Cap nhat $dll -> $(Get-DllVersion $sysDll)"
    }
}

# 2. Model: YOLOv8 (xe) + YOLOv9 (bien so) + OCR bien so
Write-Host "[2/5] Kiem tra model" -ForegroundColor Cyan
if (-not (Test-Path "models\yolov8n.pt")) { throw "Thieu models\yolov8n.pt" }
Invoke-Checked $py -c @"
import pathlib
from fast_plate_ocr.inference import hub as ocr_hub
from open_image_models.detection.core import hub as det_hub
d = pathlib.Path('models/plates')
if not (d / 'cct_s_v2_global.onnx').exists() or not (d / 'cct_s_v2_global_plate_config.yaml').exists():
    ocr_hub.download_model('cct-s-v2-global-model', save_directory=d)
if not (d / 'yolo-v9-t-384-license-plates-end2end.onnx').exists():
    det_hub.download_model('yolo-v9-t-384-license-plate-end2end', save_directory=d)
print('Plate models OK')
"@

# 3. PyInstaller (onedir: khoi dong nhanh, khong phai giai nen moi lan chay)
Write-Host "[3/5] Chay PyInstaller" -ForegroundColor Cyan
Invoke-Checked $py -m PyInstaller app.py `
    --name AutoGuardian `
    --distpath $distRoot --workpath "build\$(Split-Path $distRoot -Leaf)" `
    --noconfirm --clean --windowed --onedir `
    --collect-all ultralytics `
    --hidden-import lap --copy-metadata lap `
    --exclude-module tkinter

# 4. Du lieu nguoi dung dat canh exe (de sua config, xem ket qua)
Write-Host "[4/5] Sao chep configs, models, outputs" -ForegroundColor Cyan
$dist = "$distRoot\AutoGuardian"
Copy-Item configs -Destination $dist -Recurse -Force
New-Item -ItemType Directory -Force "$dist\models\plates" | Out-Null
Copy-Item "models\yolov8n.pt" "$dist\models\" -Force
Copy-Item "models\plates\*.onnx", "models\plates\*.yaml" "$dist\models\plates\" -Force
foreach ($d in "captures", "recordings", "reports", "logs") {
    New-Item -ItemType Directory -Force "$dist\outputs\$d" | Out-Null
}

# 5. Nen zip de chia se
if (-not $NoZip) {
    Write-Host "[5/5] Nen $zipName" -ForegroundColor Cyan
    # Tu chia thanh nhieu phan < 2 GB (gioi han file dinh kem cua GitHub Release)
    Invoke-Checked $py tools\package_release.py $dist "dist\$zipName"
}

$sizeMB = [math]::Round(((Get-ChildItem $dist -Recurse | Measure-Object Length -Sum).Sum / 1MB), 0)
Write-Host "Xong: $dist\AutoGuardian.exe ($sizeMB MB)" -ForegroundColor Green
