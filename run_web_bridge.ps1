# BananaBrain Web Bridge 실행 스크립트
# 사용법: .\run_web_bridge.ps1

$ErrorActionPreference = "Stop"

$venvActivate = "C:\Users\dc99.lee\Envs\v1\Scripts\Activate.ps1"
$manageScript = Join-Path $PSScriptRoot "AI\python\web_bridge\manage.py"

if (-not (Test-Path $venvActivate)) {
    Write-Error "v1 가상환경을 찾을 수 없습니다: $venvActivate"
    exit 1
}

Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned
& $venvActivate

Write-Host ""
Write-Host "=== BananaBrain Web Bridge ===" -ForegroundColor Yellow
Write-Host "  URL  : http://127.0.0.1:8010/" -ForegroundColor Cyan
Write-Host "  UDP 수신 (C++→Django) : port 37000" -ForegroundColor Green
Write-Host "  UDP 송신 (Django→C++) : port 37001" -ForegroundColor Green
Write-Host "  종료 : Ctrl+C" -ForegroundColor Gray
Write-Host ""

python $manageScript runserver 127.0.0.1:8010 --noreload
