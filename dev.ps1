#!/usr/bin/env pwsh
# ============================================
#  MenuScan - Dev Task Runner
#  Usage: .\dev.ps1 <command>
#
#  Native workflow: db + redis run in Docker,
#  backend and frontend run locally via uv / npm.
# ============================================

param(
    # dev command, e.g. be / fe / test.
    [Parameter(Position = 0)]
    [string]$Command,

    # Remaining positional args (e.g. test file paths) forwarded to the command.
    [Parameter(ValueFromRemainingArguments)]
    [string[]]$RemainingArgs
)

$ErrorActionPreference = "Stop"

$Root    = $PSScriptRoot
$EnvFile = Join-Path $Root "env\.env.local"
$AppDir  = Join-Path $Root "app"
$FeDir   = Join-Path $Root "frontend"

function Invoke-LoadEnv {
    if (-not (Test-Path $EnvFile)) {
        Write-Host "  Missing $EnvFile." -ForegroundColor Red
        Write-Host "  Create it: Copy-Item env\.env.local.example env\.env.local" -ForegroundColor DarkGray
        exit 1
    }
    Get-Content $EnvFile | ForEach-Object {
        $line = $_.Trim()
        if (-not $line -or $line.StartsWith('#') -or -not $line.Contains('=')) { return }
        $i = $line.IndexOf('=')
        $k = $line.Substring(0, $i).Trim()
        $v = $line.Substring($i + 1).Trim().Trim('"').Trim("'")
        Set-Item -Path "Env:$k" -Value $v
    }
}

function Invoke-InDir {
    param([string]$Path, [scriptblock]$Action)
    Push-Location $Path
    try { & $Action } finally { Pop-Location }
}

function Show-Help {
    Write-Host ""
    Write-Host "  MenuScan Dev Commands" -ForegroundColor Cyan
    Write-Host "  =====================" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Dependencies (Docker: db + redis)" -ForegroundColor Yellow
    Write-Host "    .\dev.ps1 up         " -NoNewline; Write-Host "Start db + redis" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 down       " -NoNewline; Write-Host "Stop db + redis" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 restart    " -NoNewline; Write-Host "Restart db + redis" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 reset      " -NoNewline; Write-Host "Wipe volumes & restart db + redis" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 status     " -NoNewline; Write-Host "Show container status" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 logs       " -NoNewline; Write-Host "Tail db + redis logs" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 logs-db    " -NoNewline; Write-Host "Tail db logs" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 logs-redis " -NoNewline; Write-Host "Tail redis logs" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 shell-db   " -NoNewline; Write-Host "Open psql console" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Native app" -ForegroundColor Yellow
    Write-Host "    .\dev.ps1 be         " -NoNewline; Write-Host "Migrate + start backend (uvicorn, reload)" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 fe         " -NoNewline; Write-Host "Start frontend (Vite)" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 migrate    " -NoNewline; Write-Host "Apply backend migrations" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 test       " -NoNewline; Write-Host "Run backend tests (pytest [args])" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 test-be    " -NoNewline; Write-Host "Alias for test" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Quality" -ForegroundColor Yellow
    Write-Host "    .\dev.ps1 lint       " -NoNewline; Write-Host "Lint backend + frontend" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 lint-be    " -NoNewline; Write-Host "Lint backend (ruff)" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 lint-fe    " -NoNewline; Write-Host "Lint frontend (eslint)" -ForegroundColor DarkGray
    Write-Host ""
}

switch ($Command) {
    # -- Dependencies (Docker: db + redis) --
    "up"         {
        docker compose up -d db redis
        Write-Host "  Dependencies up. Next: .\dev.ps1 be" -ForegroundColor Green
    }
    "down"       { docker compose down }
    "restart"    { docker compose down; docker compose up -d db redis }
    "reset"      {
        Write-Host "  Wiping volumes and restarting db + redis..." -ForegroundColor Yellow
        docker compose down -v
        docker compose up -d db redis
    }
    "status"     { docker compose ps }
    "logs"       { docker compose logs -f db redis }
    "logs-db"    { docker compose logs -f db }
    "logs-redis" { docker compose logs -f redis }
    "shell-db"   { docker compose exec db psql -U menuscan }

    # -- Native app --
    "be"         {
        Invoke-LoadEnv
        Invoke-InDir $AppDir {
            Write-Host "  Running migrations..." -ForegroundColor Cyan
            uv run alembic upgrade head
            $port = if ($env:BACKEND_PORT) { $env:BACKEND_PORT } else { '8000' }
            Write-Host "  Backend on http://localhost:$port (reload) - Ctrl+C to stop" -ForegroundColor Cyan
            uv run uvicorn main:app --reload --host 0.0.0.0 --port $port
        }
    }
    "fe"         {
        Invoke-LoadEnv
        Invoke-InDir $FeDir {
            $port = if ($env:FRONTEND_PORT) { $env:FRONTEND_PORT } else { '5173' }
            Write-Host "  Frontend on http://localhost:$port - Ctrl+C to stop" -ForegroundColor Cyan
            npm run dev -- --host 0.0.0.0 --port $port
        }
    }
    "migrate"    {
        Invoke-LoadEnv
        Invoke-InDir $AppDir { uv run alembic upgrade head }
    }
    "test"       {
        Invoke-LoadEnv
        Invoke-InDir $AppDir { uv run pytest --tb=short @RemainingArgs }
    }
    "test-be"    {
        Invoke-LoadEnv
        Invoke-InDir $AppDir { uv run pytest --tb=short @RemainingArgs }
    }

    # -- Quality --
    "lint"       {
        Write-Host "  Backend lint..." -ForegroundColor Cyan
        Invoke-InDir $AppDir { uv run ruff check . }
        Write-Host "  Frontend lint..." -ForegroundColor Cyan
        Invoke-InDir $FeDir { npm run lint }
    }
    "lint-be"    { Invoke-InDir $AppDir { uv run ruff check . } }
    "lint-fe"    { Invoke-InDir $FeDir { npm run lint } }

    default      { Show-Help }
}
