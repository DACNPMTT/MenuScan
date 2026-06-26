#!/usr/bin/env pwsh

param(
    [Parameter(Position = 0)]
    [ValidateSet("start", "stop", "restart", "status", "logs")]
    [string]$Command = "start",

    [int]$BackendPort = 8000,
    [int]$FrontendPort = 5173,
    [int]$DbPort = 54321,
    [int]$RedisPort = 63790
)

$ErrorActionPreference = "Stop"

$Root = $PSScriptRoot
$AppDir = Join-Path $Root "app"
$FrontendDir = Join-Path $Root "frontend"
$RunDir = Join-Path $env:TEMP "menuscan-run"
$BackendPidFile = Join-Path $RunDir "backend.pid"
$FrontendPidFile = Join-Path $RunDir "frontend.pid"
$BackendOutLog = Join-Path $RunDir "backend.out.log"
$BackendErrLog = Join-Path $RunDir "backend.err.log"
$FrontendOutLog = Join-Path $RunDir "frontend.out.log"
$FrontendErrLog = Join-Path $RunDir "frontend.err.log"

function Write-Step([string]$Message) {
    Write-Host "==> $Message" -ForegroundColor Cyan
}

function Write-Ok([string]$Message) {
    Write-Host "OK  $Message" -ForegroundColor Green
}

function Ensure-RunDir {
    New-Item -ItemType Directory -Force -Path $RunDir | Out-Null
}

function Test-CommandExists([string]$Name) {
    return [bool](Get-Command $Name -ErrorAction SilentlyContinue)
}

function Wait-HttpOk([string]$Url, [int]$Seconds = 30) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    do {
        try {
            Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 | Out-Null
            return
        }
        catch {
            Start-Sleep -Seconds 1
        }
    } while ((Get-Date) -lt $deadline)

    throw "Timed out waiting for $Url"
}

function Test-HttpOk([string]$Url) {
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 3 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Get-ListeningProcessId([int]$Port) {
    $line = netstat -ano |
        Select-String "127\.0\.0\.1:$Port\s+.*LISTENING\s+(\d+)" |
        Select-Object -First 1

    if ($line -and $line.Matches[0].Groups.Count -gt 1) {
        return $line.Matches[0].Groups[1].Value
    }

    return $null
}

function Wait-DockerReady {
    docker info *> $null
    if ($LASTEXITCODE -eq 0) {
        return
    }

    $dockerDesktop = "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    if (Test-Path $dockerDesktop) {
        Write-Step "Starting Docker Desktop"
        Start-Process -FilePath $dockerDesktop -WindowStyle Hidden
    }

    $deadline = (Get-Date).AddMinutes(3)
    do {
        Start-Sleep -Seconds 5
        docker info *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
    } while ((Get-Date) -lt $deadline)

    throw "Docker is not ready. Open Docker Desktop, then run .\run.ps1 start again."
}

function Stop-ProcessFromPidFile([string]$PidFile, [string]$Name) {
    if (-not (Test-Path $PidFile)) {
        return
    }

    $processId = Get-Content $PidFile -ErrorAction SilentlyContinue
    if ($processId) {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Write-Ok "Stopped $Name process $processId"
    }
    Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
}

function Stop-App {
    Write-Step "Stopping native backend/frontend"
    Stop-ProcessFromPidFile $BackendPidFile "backend"
    Stop-ProcessFromPidFile $FrontendPidFile "frontend"
}

function Start-Dependencies {
    if (-not (Test-CommandExists "docker")) {
        throw "Docker is required but was not found."
    }

    Wait-DockerReady

    $env:DB_PORT = "$DbPort"
    $env:REDIS_PORT = "$RedisPort"

    Write-Step "Starting Postgres and Redis"
    docker compose up -d --remove-orphans db redis

    Write-Step "Waiting for Postgres health"
    $deadline = (Get-Date).AddMinutes(2)
    do {
        Start-Sleep -Seconds 3
        $status = docker inspect --format "{{.State.Health.Status}}" menuscan-db 2>$null
    } while ($status -ne "healthy" -and (Get-Date) -lt $deadline)

    if ($status -ne "healthy") {
        throw "Postgres did not become healthy."
    }
}

function Run-Migrations {
    $python = Join-Path $AppDir ".venv\Scripts\python.exe"
    if (-not (Test-Path $python)) {
        throw "Backend venv not found at $python. Run dependency install first."
    }

    $env:DATABASE_URL = "postgresql://menuscan:localdev@127.0.0.1:$DbPort/menuscan"

    Write-Step "Running Alembic migrations"
    Push-Location $AppDir
    try {
        & $python -m alembic upgrade head
    }
    finally {
        Pop-Location
    }
}

function Start-Backend {
    $python = Join-Path $AppDir ".venv\Scripts\python.exe"
    $env:DATABASE_URL = "postgresql://menuscan:localdev@127.0.0.1:$DbPort/menuscan"
    $env:API_V1_PREFIX = "/api/v1"
    $env:CORS_ORIGINS = "http://localhost:$FrontendPort,http://127.0.0.1:$FrontendPort"

    if (
        (Test-HttpOk "http://127.0.0.1:$BackendPort/health") -and
        (Test-HttpOk "http://127.0.0.1:$BackendPort/ready")
    ) {
        $existingPid = Get-ListeningProcessId $BackendPort
        if ($existingPid) {
            Set-Content -Path $BackendPidFile -Value $existingPid
        }
        Write-Ok "Backend already running on http://127.0.0.1:$BackendPort"
        return
    }

    Write-Step "Starting backend on http://127.0.0.1:$BackendPort"
    $process = Start-Process `
        -FilePath $python `
        -ArgumentList @("-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "$BackendPort") `
        -WorkingDirectory $AppDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $BackendOutLog `
        -RedirectStandardError $BackendErrLog `
        -PassThru

    Set-Content -Path $BackendPidFile -Value $process.Id
    Wait-HttpOk "http://127.0.0.1:$BackendPort/health"
    Wait-HttpOk "http://127.0.0.1:$BackendPort/ready"
}

function Start-Frontend {
    $npm = (Get-Command "npm.cmd" -ErrorAction SilentlyContinue).Source
    if (-not $npm) {
        throw "npm.cmd was not found. Install Node.js first."
    }

    $env:VITE_API_URL = "http://127.0.0.1:$BackendPort"

    if (Test-HttpOk "http://127.0.0.1:$FrontendPort") {
        $existingPid = Get-ListeningProcessId $FrontendPort
        if ($existingPid) {
            Set-Content -Path $FrontendPidFile -Value $existingPid
        }
        Write-Ok "Frontend already running on http://127.0.0.1:$FrontendPort"
        return
    }

    Write-Step "Starting frontend on http://127.0.0.1:$FrontendPort"
    $process = Start-Process `
        -FilePath $npm `
        -ArgumentList @("run", "dev", "--", "--host", "127.0.0.1", "--port", "$FrontendPort") `
        -WorkingDirectory $FrontendDir `
        -WindowStyle Hidden `
        -RedirectStandardOutput $FrontendOutLog `
        -RedirectStandardError $FrontendErrLog `
        -PassThru

    Set-Content -Path $FrontendPidFile -Value $process.Id
    Wait-HttpOk "http://127.0.0.1:$FrontendPort"
}

function Start-App {
    Ensure-RunDir
    Stop-App
    Start-Dependencies
    Run-Migrations
    Start-Backend
    Start-Frontend

    Write-Host ""
    Write-Ok "MenuScan is running"
    Write-Host "Frontend : http://127.0.0.1:$FrontendPort"
    Write-Host "Backend  : http://127.0.0.1:$BackendPort"
    Write-Host "Health   : http://127.0.0.1:$BackendPort/health"
    Write-Host "Ready    : http://127.0.0.1:$BackendPort/ready"
    Write-Host ""
    Write-Host "Stop with: .\run.ps1 stop"
}

function Show-Status {
    Write-Step "Docker services"
    docker compose ps

    Write-Host ""
    Write-Step "Native app ports"
    netstat -ano | Select-String ":$BackendPort|:$FrontendPort|:$DbPort|:$RedisPort" `
        | ForEach-Object { Write-Host $_ }
}

function Show-Logs {
    Write-Host ""
    Write-Step "Backend stderr"
    if (Test-Path $BackendErrLog) { Get-Content $BackendErrLog -Tail 80 }

    Write-Host ""
    Write-Step "Frontend stdout"
    if (Test-Path $FrontendOutLog) { Get-Content $FrontendOutLog -Tail 80 }
}

switch ($Command) {
    "start" {
        Start-App
    }
    "stop" {
        Stop-App
    }
    "restart" {
        Start-App
    }
    "status" {
        Show-Status
    }
    "logs" {
        Show-Logs
    }
}
