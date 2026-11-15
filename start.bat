@echo off
REM Chạy NetJudge từ cmd hoặc bằng cách bấm đúp. Thực chất gọi start.ps1.
chcp 65001 >nul
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start.ps1"
