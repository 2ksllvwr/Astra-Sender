$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
try {
    if (-not (Test-Path '.git')) { throw 'Projeto ainda nao conectado. Execute INICIAR_GITHUB.bat antes.' }
    if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Git nao encontrado no PATH.' }
    & git add -A
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao adicionar arquivos.' }
    & git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        & git commit -m 'chore: atualizar Astra Sender'
        if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar commit.' }
    } else { Write-Host 'Nao ha alteracoes a enviar.' }
    & git push origin main
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao enviar atualizacao ao GitHub.' }
    Write-Host 'Atualizacao enviada. Build disponivel na aba Actions.' -ForegroundColor Green
    Write-Host 'https://github.com/2ksllvwr/Astra-Sender/actions'
} catch {
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
