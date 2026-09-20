$ErrorActionPreference = "Stop"
if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example. Change POSTGRES_PASSWORD before long-term use." -ForegroundColor Yellow
}
docker compose up -d --build
Write-Host ""
Write-Host "Cognitive Twin Genesis is starting." -ForegroundColor Green
Write-Host "API docs: http://localhost:8000/docs"
Write-Host "Health:   http://localhost:8000/api/v1/health"
