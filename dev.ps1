#!/usr/bin/env pwsh
# ============================================
#  MenuScan — Dev Task Runner
#  Usage: .\dev.ps1 <command>
# ============================================

param(
    [Parameter(Position = 0)]
    [string]$Command
)

$ErrorActionPreference = "Stop"

function Show-Help {
    Write-Host ""
    Write-Host "  MenuScan Dev Commands" -ForegroundColor Cyan
    Write-Host "  =====================" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Lifecycle" -ForegroundColor Yellow
    Write-Host "    .\dev.ps1 up        " -NoNewline; Write-Host "Build & start all services" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 down      " -NoNewline; Write-Host "Stop all services" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 restart   " -NoNewline; Write-Host "Rebuild & restart" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 reset     " -NoNewline; Write-Host "Wipe DB volume & rebuild" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 status    " -NoNewline; Write-Host "Show service status" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Logs" -ForegroundColor Yellow
    Write-Host "    .\dev.ps1 logs      " -NoNewline; Write-Host "Tail all service logs" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 logs-be   " -NoNewline; Write-Host "Tail backend logs only" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 logs-fe   " -NoNewline; Write-Host "Tail frontend logs only" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Quality" -ForegroundColor Yellow
    Write-Host "    .\dev.ps1 test      " -NoNewline; Write-Host "Run backend tests" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 lint      " -NoNewline; Write-Host "Lint backend + frontend" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 lint-be   " -NoNewline; Write-Host "Lint backend only" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 lint-fe   " -NoNewline; Write-Host "Lint frontend only" -ForegroundColor DarkGray
    Write-Host ""
    Write-Host "  Shell" -ForegroundColor Yellow
    Write-Host "    .\dev.ps1 shell-be  " -NoNewline; Write-Host "Open backend shell" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 shell-fe  " -NoNewline; Write-Host "Open frontend shell" -ForegroundColor DarkGray
    Write-Host "    .\dev.ps1 shell-db  " -NoNewline; Write-Host "Open psql console" -ForegroundColor DarkGray
    Write-Host ""
}

switch ($Command) {
    # ── Lifecycle ──
    "up"       { docker compose up --build -d; docker compose logs -f }
    "down"     { docker compose down }
    "restart"  { docker compose down; docker compose up --build -d; docker compose logs -f }
    "reset"    {
        Write-Host "  Wiping database volume and rebuilding..." -ForegroundColor Yellow
        docker compose down -v
        docker compose up --build -d
        docker compose logs -f
    }
    "status"   { docker compose ps }

    # ── Logs ──
    "logs"     { docker compose logs -f }
    "logs-be"  { docker compose logs -f backend }
    "logs-fe"  { docker compose logs -f frontend }

    # ── Quality ──
    "test"     { docker compose exec backend uv run pytest --tb=short }
    "lint"     {
        Write-Host "  Backend lint..." -ForegroundColor Cyan
        docker compose exec backend uv run ruff check .
        Write-Host "  Frontend lint..." -ForegroundColor Cyan
        docker compose exec frontend npm run lint
    }
    "lint-be"  { docker compose exec backend uv run ruff check . }
    "lint-fe"  { docker compose exec frontend npm run lint }

    # ── Shell ──
    "shell-be" { docker compose exec backend bash }
    "shell-fe" { docker compose exec frontend sh }
    "shell-db" { docker compose exec db psql -U menuscan }

    default    { Show-Help }
}
