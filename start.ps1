# Khởi động NetJudge: bật Docker Desktop nếu cần, build web nếu chưa có, rồi chạy server cổng 3000.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker chưa chạy, đang mở Docker Desktop..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    for ($i = 0; $i -lt 60; $i++) { Start-Sleep 3; docker info *> $null; if ($LASTEXITCODE -eq 0) { break } }
}
docker image inspect netjudge-runner:1 *> $null
if ($LASTEXITCODE -ne 0) { python judge/judge.py build }

Set-Location web
if (-not (Test-Path node_modules)) { npm install --no-audit --no-fund }
if (-not (Test-Path .next)) { npx next build }
Write-Host "NetJudge chạy tại http://localhost:3000  (Ctrl+C để dừng)"
npx next start -H 0.0.0.0 -p 3000
