@echo off
cd /d "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0PUBLICAR_VERSAO.ps1"
set "RESULTADO=%ERRORLEVEL%"
echo.
if not "%RESULTADO%"=="0" echo Ocorreu um problema. Verifique o erro mostrado acima.
pause
exit /b %RESULTADO%
