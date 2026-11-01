$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Fail-IfError([string]$step) {
    if ($LASTEXITCODE -ne 0) { throw "Falha em: $step (codigo $LASTEXITCODE)." }
}

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable('Path', 'Machine')
    $user = [Environment]::GetEnvironmentVariable('Path', 'User')
    $env:Path = "$machine;$user;$env:Path"
}

function Get-Exe([string]$command, [string]$packageId) {
    $found = Get-Command $command -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Falta '$command'. Instale Git e GitHub CLI ou habilite o winget (App Installer)."
    }
    Write-Host "Instalando $packageId via winget..." -ForegroundColor Cyan
    & winget install --id $packageId --exact --source winget --accept-package-agreements --accept-source-agreements
    Fail-IfError "instalacao de $packageId"
    Refresh-Path
    $found = Get-Command $command -ErrorAction SilentlyContinue
    if ($found) { return $found.Source }
    $paths = if ($command -eq 'git') {
        @("$env:ProgramFiles\Git\cmd\git.exe", "$env:ProgramFiles\Git\bin\git.exe")
    } else {
        @("$env:ProgramFiles\GitHub CLI\gh.exe", "$env:LOCALAPPDATA\Programs\GitHub CLI\gh.exe")
    }
    foreach ($file in $paths) { if (Test-Path $file) { return $file } }
    throw "'$command' foi instalado, mas nao foi encontrado. Feche e reabra esta janela e tente de novo."
}

try {
    Write-Host '===========================================' -ForegroundColor Cyan
    Write-Host '  Astra Sender | Configuracao automatica GitHub' -ForegroundColor Cyan
    Write-Host '===========================================' -ForegroundColor Cyan
    $git = Get-Exe 'git' 'Git.Git'
    $gh = Get-Exe 'gh' 'GitHub.cli'

    & $gh auth status --hostname github.com 2>$null | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Faça login em sua conta pelo navegador do GitHub CLI.' -ForegroundColor Yellow
        & $gh auth login --hostname github.com --web --git-protocol https
        Fail-IfError 'login no GitHub'
    }
    $login = (& $gh api user --jq '.login').Trim()
    Fail-IfError 'verificar conta'
    if ($login -ne '2ksllvwr') {
        throw "Conta conectada: '$login'. Esperado: '2ksllvwr'. Conecte a conta correta no GitHub CLI."
    }

    if (-not (Test-Path (Join-Path $PSScriptRoot '.git'))) {
        & $git init -b main
        Fail-IfError 'inicializar Git'
    }
    $name = & $git config --local user.name
    if (-not $name) { & $git config --local user.name $login; Fail-IfError 'identidade Git' }
    $email = & $git config --local user.email
    if (-not $email) { & $git config --local user.email "$login@users.noreply.github.com"; Fail-IfError 'e-mail Git' }

    & $git add -A
    Fail-IfError 'adicionar arquivos'
    & $git diff --cached --quiet
    if ($LASTEXITCODE -ne 0) {
        & $git commit -m 'feat: Astra Sender 0.2.4 beta e compilacao automatica'
        Fail-IfError 'criar commit inicial'
    } else {
        Write-Host 'Nenhuma alteracao pendente para commit.'
    }

    $repo = '2ksllvwr/Astra-Sender'
    & $gh repo view $repo --json name --jq '.name' 2>$null | Out-Null
    $exists = ($LASTEXITCODE -eq 0)
    if (-not $exists) {
        Write-Host 'Criando repositorio PRIVADO Astra Sender e enviando arquivos...' -ForegroundColor Cyan
        & $gh repo create $repo --private --description 'Astra Sender - macros de mensagens para Windows, agendamento e perfis' --source . --remote origin --push
        Fail-IfError 'criar repositorio e publicar codigo'
    } else {
        Write-Host 'Repositorio ja existe; verificando remote e publicando sem forcar historico.' -ForegroundColor Cyan
        $remotes = @(& $git remote)
        if ($remotes -notcontains 'origin') {
            & $git remote add origin "https://github.com/$repo.git"
            Fail-IfError 'configurar remote'
        } else {
            $origin = (& $git remote get-url origin).Trim()
            if ($origin -notmatch '(github\.com[:/])2ksllvwr/Astra-Sender(\.git)?$') {
                throw "Remote origin existente aponta para outro repositorio: $origin"
            }
        }
        & $git push -u origin main
        Fail-IfError 'enviar branch main'
    }

    $tag = 'v0.2.4-beta.1'
    $remoteTag = @(& $git ls-remote --tags origin "refs/tags/$tag")
    Fail-IfError 'consultar tags remotas'
    if (-not $remoteTag) {
        $localTag = @(& $git tag --list $tag)
        if (-not $localTag) {
            & $git tag -a $tag -m 'Primeiro pre-lancamento automatico do Astra Sender'
            Fail-IfError 'criar tag beta'
        }
        & $git push origin $tag
        Fail-IfError 'enviar tag beta'
    }

    Write-Host ''
    Write-Host 'Configuracao concluida. O GitHub agora pode compilar o executavel.' -ForegroundColor Green
    Write-Host 'Repositorio: https://github.com/2ksllvwr/Astra-Sender'
    Write-Host 'Actions:     https://github.com/2ksllvwr/Astra-Sender/actions'
    Write-Host 'Releases:    https://github.com/2ksllvwr/Astra-Sender/releases'
    Write-Host 'A compilacao e os envios reais ao Windows ainda precisam de validacao.' -ForegroundColor Yellow
} catch {
    Write-Host "ERRO: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}
