docker compose ps
Write-Host ""
try {
    Invoke-RestMethod http://localhost:8000/api/v1/health | ConvertTo-Json
} catch {
    Write-Host "API is not reachable yet." -ForegroundColor Yellow
}
