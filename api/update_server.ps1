# update_server.ps1 — Auto-updater do servidor Invec
# Registrado pelo instalador como Scheduled Task (InvecAutoUpdate)
# Executa: no startup (+5 min) e diariamente às 17h

$InstallDir  = Split-Path -Parent $MyInvocation.MyCommand.Definition
$LogFile     = Join-Path $InstallDir "logs\update_server.log"
$EnvFile     = Join-Path $InstallDir ".env"
$VersionFile = Join-Path $InstallDir "server_version.txt"
$ServiceName = "InvecAPI"
$AssetName   = "InvecServidor.exe"
$Repo        = "deivydgarcez/inventario-app"   # prod: mplarlon/Invec

New-Item -ItemType Directory -Force -Path (Join-Path $InstallDir "logs") | Out-Null

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Add-Content -Path $LogFile -Value "[$ts] $msg" -Encoding UTF8
}

function Read-Env {
    $map = @{}
    if (-not (Test-Path $EnvFile)) { return $map }
    Get-Content $EnvFile -Encoding UTF8 | ForEach-Object {
        if ($_ -match "^([^#=\s][^=]*)=(.*)$") {
            $map[$matches[1].Trim()] = $matches[2].Trim()
        }
    }
    return $map
}

function Get-CurrentVersion {
    if (Test-Path $VersionFile) { return (Get-Content $VersionFile -Encoding UTF8).Trim() }
    return "0.0.0"
}

function Set-CurrentVersion($v) {
    $v | Set-Content -Path $VersionFile -Encoding UTF8
}

function Compare-IsNewer($remote, $current) {
    $r = $remote.Split('.') | ForEach-Object { [int]$_ }
    $c = $current.Split('.') | ForEach-Object { [int]$_ }
    $len = [Math]::Max($r.Count, $c.Count)
    for ($i = 0; $i -lt $len; $i++) {
        $rv = if ($i -lt $r.Count) { $r[$i] } else { 0 }
        $cv = if ($i -lt $c.Count) { $c[$i] } else { 0 }
        if ($rv -gt $cv) { return $true }
        if ($rv -lt $cv) { return $false }
    }
    return $false
}

function Send-Discord($webhook, $title, $description, $color) {
    if (-not $webhook) { return }
    try {
        $body = @{
            embeds = @(@{
                title       = $title
                description = $description
                color       = $color
                timestamp   = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
            })
        } | ConvertTo-Json -Depth 5
        Invoke-RestMethod -Uri $webhook -Method Post -Body $body `
            -ContentType "application/json" -TimeoutSec 10 | Out-Null
    } catch {}
}

function Get-ServiceStatus {
    $svc = Get-Service -Name $ServiceName -ErrorAction SilentlyContinue
    if ($null -eq $svc) { return "absent" }
    return $svc.Status
}

# ── Início ────────────────────────────────────────────────────────────────────

$env            = Read-Env
$token          = $env["GITHUB_TOKEN"]
$webhook        = $env["DISCORD_WEBHOOK"]
$versaoAtual    = Get-CurrentVersion

Write-Log "=== Verificando atualização — versão atual: $versaoAtual ==="

if (-not $token) {
    Write-Log "GITHUB_TOKEN não encontrado no .env — atualização impossível"
    exit 1
}

$mainExe   = Join-Path $InstallDir $AssetName
$tmpExe    = Join-Path $InstallDir "InvecServidor_new.exe"
$backupExe = Join-Path $InstallDir "InvecServidor_backup.exe"

try {
    # ── Checar GitHub ─────────────────────────────────────────────────────────
    $headers = @{
        "Authorization"       = "Bearer $token"
        "Accept"              = "application/vnd.github+json"
        "X-GitHub-Api-Version" = "2022-11-28"
        "User-Agent"          = "InvecUpdate/1.0"
    }

    $release = Invoke-RestMethod `
        -Uri "https://api.github.com/repos/$Repo/releases/latest" `
        -Headers $headers -TimeoutSec 15

    $tag = $release.tag_name -replace "^v", ""

    if (-not $tag) {
        Write-Log "Release sem tag_name válido"
        exit 0
    }

    if (-not (Compare-IsNewer $tag $versaoAtual)) {
        Write-Log "Sem atualização (remota: $tag  atual: $versaoAtual)"
        exit 0
    }

    Write-Log "Nova versão encontrada: $tag"

    $asset = $release.assets | Where-Object { $_.name -eq $AssetName } | Select-Object -First 1
    if (-not $asset) {
        Write-Log "Asset '$AssetName' não encontrado no release $tag"
        exit 0
    }

    # ── Download ──────────────────────────────────────────────────────────────
    Write-Log "Baixando $AssetName..."

    $dlHeaders = @{
        "Authorization" = "Bearer $token"
        "Accept"        = "application/octet-stream"
        "User-Agent"    = "InvecUpdate/1.0"
    }
    Invoke-WebRequest -Uri $asset.url -Headers $dlHeaders `
        -OutFile $tmpExe -TimeoutSec 180

    Write-Log "Download concluído"

    # ── Substituir executável ─────────────────────────────────────────────────
    Write-Log "Parando serviço..."
    Stop-Service -Name $ServiceName -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2

    if (Test-Path $mainExe) { Copy-Item $mainExe $backupExe -Force }
    Move-Item $tmpExe $mainExe -Force
    Write-Log "Executável substituído"

    # ── Reiniciar serviço ─────────────────────────────────────────────────────
    Write-Log "Iniciando serviço..."
    Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 3

    if ((Get-ServiceStatus) -ne "Running") {
        throw "Serviço não iniciou após atualização — realizando rollback"
    }

    Set-CurrentVersion $tag
    Write-Log "✅ Atualização concluída: $versaoAtual → $tag"

    if (Test-Path $backupExe) { Remove-Item $backupExe -Force }

    $notas = ""
    if ($release.body) {
        $corpo = $release.body.Trim()
        $trecho = $corpo.Substring(0, [Math]::Min(900, $corpo.Length))
        $notas = "`n`n**O que há de novo:**`n$trecho"
    }
    Send-Discord $webhook `
        "✅ Servidor Invec atualizado — v$tag" `
        "Atualização automática concluída.`n**Anterior:** $versaoAtual`n**Atual:** $tag$notas" `
        0x2E7D32

} catch {
    $errMsg     = $_.Exception.Message
    $errDetails = $_ | Out-String

    Write-Log "❌ Erro: $errMsg`n$errDetails"

    # ── Rollback ──────────────────────────────────────────────────────────────
    if ((Test-Path $backupExe) -and (Get-ServiceStatus) -ne "Running") {
        Write-Log "Aplicando rollback..."
        try {
            Copy-Item $backupExe $mainExe -Force
            Start-Service -Name $ServiceName -ErrorAction SilentlyContinue
            Start-Sleep -Seconds 3
            if ((Get-ServiceStatus) -eq "Running") {
                Write-Log "Rollback bem-sucedido — serviço restaurado"
            } else {
                Write-Log "Rollback falhou — serviço não subiu. Intervenção manual necessária."
            }
        } catch {
            Write-Log "Erro durante rollback: $_"
        }
    }

    if (Test-Path $tmpExe) { Remove-Item $tmpExe -Force -ErrorAction SilentlyContinue }

    $limite     = [Math]::Min(700, $errDetails.Length)
    $trecho     = $errDetails.Substring(0, $limite)
    $discordMsg = "**Versão atual:** $versaoAtual`n**Erro:** $errMsg`n``````n$trecho`n``````"

    Send-Discord $webhook `
        "❌ Erro na atualização do servidor Invec" `
        $discordMsg `
        0xC62828
}
