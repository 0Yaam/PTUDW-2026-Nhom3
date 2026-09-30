@echo off
setlocal
cd /d %~dp0

powershell.exe -NoProfile -ExecutionPolicy Bypass -File %~dp0start-all.ps1 %*
set EXIT_CODE=%ERRORLEVEL%

if not %EXIT_CODE%==0 (
    echo.
    echo Khoi dong that bai. Kiem tra Docker Desktop va cac port 3000, 5432, 8000.
    pause
)

exit /b %EXIT_CODE%
