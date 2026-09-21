# PowerShell Script for Culinary Blog Project
param (
    [ValidateSet("docker", "frontend", "check", "down", "local", "help")]
    [string]$Mode = "docker"
)

$ErrorActionPreference = "Stop"
$RootPath = $PSScriptRoot

function Show-Title {
    param([string]$text)
    Write-Host "`n--- $text ---" -ForegroundColor Cyan
}

function Show-Success {
    param([string]$text)
    Write-Host "[Ok] $text" -ForegroundColor Green
}

function Show-Info {
    param([string]$text)
    Write-Host "[Info] $text" -ForegroundColor Yellow
}

function Show-Error {
    param([string]$text)
    Write-Host "[Error] $text" -ForegroundColor Red
}

function Confirm-Command {
    param([string]$name)
    if ($LASTEXITCODE -ne 0) {
        throw "$name failed with exit code $LASTEXITCODE."
    }
}

function Get-UvExecutable {
    $uvCommand = Get-Command "uv" -ErrorAction SilentlyContinue
    if ($uvCommand) {
        return $uvCommand.Source
    }

    $uvFallback = Join-Path $env:USERPROFILE ".local\bin\uv.exe"
    if (Test-Path $uvFallback) {
        return $uvFallback
    }

    throw "uv was not found. Install it from https://docs.astral.sh/uv/ or add it to PATH."
}

switch ($Mode) {
    "docker" {
        Show-Title "Run Docker Compose"
        Show-Info "Dang build va khoi chay Postgres, Backend (API), Frontend (Web)..."
        
        docker compose -f "$RootPath\compose.yaml" up --build -d
        Confirm-Command "Docker Compose startup"
        
        Write-Host ""
        Show-Success "He thong da duoc khoi dong ngam thanh cong!"
        Write-Host "  - Frontend Web        : http://localhost:3000" -ForegroundColor Cyan
        Write-Host "  - Backend API Swagger : http://localhost:8000/docs" -ForegroundColor Cyan
        Write-Host "  - Backend Healthcheck : http://localhost:8000/health" -ForegroundColor Cyan
        Write-Host "  - Frontend Hot Reload : http://localhost:3001 (optional)" -ForegroundColor DarkCyan
        Show-Info "Theo doi Frontend realtime: npm run dev --prefix frontend"
        Show-Info "Xem trang thai: docker compose ps"
        Show-Info "Xem log live  : docker compose logs -f"
        Show-Info "Dung he thong : .\start-all.ps1 -Mode down"
    }

    "frontend" {
        Show-Title "Frontend Development With Hot Reload"
        Show-Info "Frontend Docker van chay tai http://localhost:3000."
        Show-Info "Dang khoi dong Frontend dev tai http://localhost:3001..."
        npm run dev --prefix "$RootPath\frontend"
    }

    "check" {
        Show-Title "Kiem Tra Code Va Build Toan Bo"
        $uvExecutable = Get-UvExecutable

        # 1. Backend Lint
        Show-Info "1/5. Kiem tra Backend Lint (Ruff)..."
        & $uvExecutable run --directory "$RootPath\backend" ruff check .
        Confirm-Command "Backend lint"
        Show-Success "Backend Lint: Passed"

        # 2. Backend Tests
        Show-Info "2/5. Chay Backend Tests (Pytest + Coverage)..."
        & $uvExecutable run --directory "$RootPath\backend" pytest --cov=culinary_blog_api
        Confirm-Command "Backend tests"
        Show-Success "Backend Tests: Passed"

        # 3. Frontend Lint
        Show-Info "3/5. Kiem tra Frontend Lint (ESLint)..."
        npm run lint --prefix "$RootPath\frontend"
        Confirm-Command "Frontend lint"
        Show-Success "Frontend Lint: Passed"

        # 4. Frontend Build
        Show-Info "4/5. Build Frontend (Next.js)..."
        npm run build --prefix "$RootPath\frontend"
        Confirm-Command "Frontend build"
        Show-Success "Frontend Build: Passed"

        # 5. Docker Build
        Show-Info "5/5. Build Docker Images..."
        docker compose -f "$RootPath\compose.yaml" build
        Confirm-Command "Docker Compose build"
        Show-Success "Docker Compose Build: Passed"

        Show-Title "Tat Ca Cac Buoc Kiem Tra Va Build Deu Thanh Cong!"
    }

    "down" {
        Show-Title "Dung He Thong Docker"
        docker compose -f "$RootPath\compose.yaml" down
        Confirm-Command "Docker Compose shutdown"
        Show-Success "Da dung tat ca cac container an toan."
    }

    "local" {
        Show-Title "Chay Truc Tiep Tren May (Local Dev)"
        Show-Info "Khoi dong Backend tren cua so moi..."
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$RootPath\backend'; uv run uvicorn culinary_blog_api.main:app --reload --port 8000"
        
        Show-Info "Khoi dong Frontend tren cua so moi..."
        Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$RootPath\frontend'; npm run dev"
        
        Show-Success "Da mo cua so chay Backend (port 8000) va Frontend dev (port 3001)."
    }

    "help" {
        Write-Host "Huong Dan Su Dung: .\start-all.ps1 [-Mode <che_do>]" -ForegroundColor Cyan
        Write-Host "  .\start-all.ps1             : Khoi dong toan bo qua Docker Compose (Mac dinh)"
        Write-Host "  .\start-all.ps1 -Mode frontend : Chay them Frontend hot reload tai port 3001"
        Write-Host "  .\start-all.ps1 -Mode check : Kiem tra lint, tests va build toan bo"
        Write-Host "  .\start-all.ps1 -Mode down  : Dung cac container Docker"
        Write-Host "  .\start-all.ps1 -Mode local : Chay dev truc tiep qua uv va npm"
    }
}
