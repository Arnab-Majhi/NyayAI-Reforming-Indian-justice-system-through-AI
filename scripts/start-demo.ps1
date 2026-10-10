$ErrorActionPreference = 'Stop'
$Root = Split-Path -Parent $PSScriptRoot
$Python = Join-Path $Root 'backend\.venv\Scripts\python.exe'
if (-not (Test-Path $Python)) { throw 'Install backend dependencies using README first.' }
foreach ($Port in @(3000, 8000)) {
    if (Get-NetTCPConnection -State Listen -LocalPort $Port -ErrorAction SilentlyContinue) {
        throw "Port $Port is already in use. Stop the existing application before starting a new demo."
    }
}
Push-Location (Join-Path $Root 'backend')
try {
    & $Python -m app.seed
    if ($LASTEXITCODE -ne 0) { throw 'Case seed failed.' }
    & $Python -m app.demo_samples
    if ($LASTEXITCODE -ne 0) { throw 'Document sample seed failed.' }
} finally { Pop-Location }
$Backend = Start-Process -FilePath $Python -ArgumentList '-m uvicorn app.main:app --host 127.0.0.1 --port 8000' -WorkingDirectory (Join-Path $Root 'backend') -RedirectStandardOutput (Join-Path $Root 'backend-demo.log') -RedirectStandardError (Join-Path $Root 'backend-demo-error.log') -PassThru
$Frontend = Start-Process -FilePath 'npm.cmd' -ArgumentList 'run start' -WorkingDirectory (Join-Path $Root 'frontend') -RedirectStandardOutput (Join-Path $Root 'frontend-demo.log') -RedirectStandardError (Join-Path $Root 'frontend-demo-error.log') -PassThru
Write-Output "Started demo processes: backend $($Backend.Id), frontend launcher $($Frontend.Id)."
Write-Output 'Open http://localhost:3000. Logs are in the repository root. This uses the last production build.'
Write-Output 'To stop: close these local processes or stop listeners on ports 3000 and 8000 after confirming their identities.'