@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0build_windows.ps1"
if errorlevel 1 echo Houve um erro na compilacao. Veja a mensagem acima.
echo.
pause
