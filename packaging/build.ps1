# ================================================================== #
# @Author: Fantasy_Silence                                           #
# @Time: 2026-11-24                                                  #
# @IDE: Visual Studio Code & PyCharm                                 #
# @Python: 3.12.7                                                    #
# ================================================================== #
# @Description: 一键打包：先构建前端，再跑 PyInstaller                 #
# ================================================================== #
# 用法：powershell -ExecutionPolicy Bypass -File packaging\build.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root ".venv\Scripts\python.exe"

if (-not (Test-Path $Python)) {
    throw "找不到工作区虚拟环境：$Python"
}

Write-Host "[1/3] 构建前端..."
Push-Location (Join-Path $Root "web")
try {
    npm run build
} finally {
    Pop-Location
}

Write-Host "[2/3] 检查 web/dist..."
if (-not (Test-Path (Join-Path $Root "web\dist\index.html"))) {
    throw "web/dist/index.html 不存在，前端构建失败"
}

Write-Host "[3/3] PyInstaller 打包..."
Push-Location $Root
try {
    # 中间产物放 .temp/，最终产物放 dist/；不要把 build/ 留在仓库里
    Write-Host "   root: [$Root]"
    $tool = Join-Path $Root ".venv\Scripts\pyinstaller.exe"
    $specFile = Join-Path $Root "packaging\Sciyardcampus_Kit.spec"
    $workDir = Join-Path $Root ".temp\build"
    $distDir = Join-Path $Root "dist"
    Write-Host "   pyinstaller: $tool"
    Write-Host "   spec: $specFile"
    $toolArgs = @($specFile, "--noconfirm", "--workpath", $workDir, "--distpath", $distDir)
    Start-Process -FilePath $tool -ArgumentList $toolArgs -Wait -NoNewWindow
} finally {
    Pop-Location
}

Write-Host "完成：dist\Sciyardcampus_Kit\Sciyardcampus_Kit.exe"
