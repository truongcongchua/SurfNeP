# Khởi động NetJudge: bật Docker Desktop nếu cần, build web nếu chưa có, rồi chạy server cổng 3000.
$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Docker chưa chạy, đang mở Docker Desktop..."
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    for ($i = 0; $i -lt 60; $i++) { Start-Sleep 3; docker info *> $null; if ($LASTEXITCODE -eq 0) { break } }
}
# Image máy chấm được tag theo mã băm của judge/Dockerfile + judge/runner/: sửa runner thì tự dựng lại, không dùng nhầm bản cũ.
python judge/judge.py ensure
if ($LASTEXITCODE -ne 0) { Write-Host "Không chuẩn bị được image máy chấm (xem lỗi ở trên)."; exit 1 }

Set-Location web
if (-not (Test-Path node_modules)) { npm install --no-audit --no-fund }
# Build lại khi chưa có bản build hoặc mã nguồn mới hơn bản build.
$stamp = Get-Item ".next/BUILD_ID" -ErrorAction SilentlyContinue
$newest = Get-ChildItem app, components, lib, package.json, next.config.mjs -Recurse -File | Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $stamp -or $newest.LastWriteTime -gt $stamp.LastWriteTime) { npx next build; if ($LASTEXITCODE -ne 0) { Write-Host "Build lỗi."; exit 1 } }
Write-Host "NetJudge chạy tại http://localhost:3000  (Ctrl+C để dừng)"
# Server sập thì tự chạy lại sau 3 giây (chỉ khi cửa sổ này còn mở; không tự chạy khi bật máy).
while ($true) {
    npx next start -H 0.0.0.0 -p 3000
    Write-Host "Server dừng (mã $LASTEXITCODE), chạy lại sau 3 giây... (Ctrl+C để thoát)"
    Start-Sleep 3
}
