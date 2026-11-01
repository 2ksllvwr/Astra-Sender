$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
Write-Host '=== Compilacao Astra Sender 0.2.4 ===' -ForegroundColor Cyan
try {
    if (Get-Command py -ErrorAction SilentlyContinue) {
        & py -3 -m venv .venv
    } elseif (Get-Command python -ErrorAction SilentlyContinue) {
        & python -m venv .venv
    } else {
        throw 'Python 3 nao encontrado. Instale Python 3.11 ou mais recente.'
    }
    if ($LASTEXITCODE -ne 0) { throw 'Falha criando ambiente Python.' }
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    & $python -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Falha instalando dependencias.' }
    & $python -m unittest discover -s tests -v
    if ($LASTEXITCODE -ne 0) { throw 'Falha nos testes; compilacao cancelada.' }
    & $python -m PyInstaller --noconfirm --clean --windowed --name AstraSender --collect-all pywinauto --hidden-import win32timezone main.py
    if ($LASTEXITCODE -ne 0) { throw 'Erro na compilacao.' }
    Write-Host ''
    Write-Host "PRONTO: $PSScriptRoot\dist\AstraSender\AstraSender.exe" -ForegroundColor Green
    exit 0
} catch {
    Write-Host "ERRO: $_" -ForegroundColor Red
    exit 1
}
