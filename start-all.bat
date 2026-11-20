@echo off
setlocal EnableExtensions
cd /d "%~dp0" || (
    echo Khong the mo thu muc du an: "%~dp0"
    exit /b 1
)

powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0start-all.ps1" %*
set "EXIT_CODE=%ERRORLEVEL%"

if not "%EXIT_CODE%"=="0" (
    echo.
    echo Lenh that bai. Xem thong bao loi o tren va dam bao Docker Desktop dang chay.
    pause
)

endlocal & exit /b %EXIT_CODE%
