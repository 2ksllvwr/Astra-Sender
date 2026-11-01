$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
try {
    if (-not (Test-Path '.git')) { throw 'Execute INICIAR_GITHUB.bat antes.' }
    $version = Read-Host 'Nome da versao (exemplo: v0.2.4-beta.1 ou v0.2.4)'
    if ($version -notmatch '^v\d+\.\d+\.\d+(-[A-Za-z0-9.-]+)?$') { throw 'Nome invalido. Use vX.Y.Z ou vX.Y.Z-beta.1.' }
    & git add -A
    if ($LASTEXITCODE -ne 0) { throw 'Falha no git add.' }
    & git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        & git commit -m "release: preparar $version"
        if ($LASTEXITCODE -ne 0) { throw 'Falha no git commit.' }
    }
    & git push origin main
    if ($LASTEXITCODE -ne 0) { throw 'Falha no push da branch principal.' }
    $existing = @(& git ls-remote --tags origin "refs/tags/$version")
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao consultar tags remotas.' }
    if ($existing -or @(& git tag --list $version)) { throw "A tag $version ja existe. Nunca sera sobrescrita." }
    & git tag -a $version -m "Astra Sender $version"
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao criar tag.' }
    & git push origin $version
    if ($LASTEXITCODE -ne 0) { throw 'Falha ao enviar tag.' }
    Write-Host "Versao $version publicada para compilacao automatica." -ForegroundColor Green
    Write-Host 'https://github.com/2ksllvwr/Astra-Sender/releases'
} catch {
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
