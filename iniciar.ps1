# AntiGravity ColdChain - Inicializador PowerShell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  ❄️  AntiGravity ColdChain - Monitor de Freezers IoT" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location "$scriptDir\backend"

if (Test-Path ".\venv\Scripts\python.exe") {
    Write-Host "[*] Ambiente virtual detectado. Iniciando servidor..." -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================================" -ForegroundColor Cyan
    Write-Host "  🚀 Servidor iniciado! Acesse: http://localhost:8000" -ForegroundColor Green
    Write-Host "========================================================" -ForegroundColor Cyan
    Write-Host ""
    Start-Process "http://localhost:8000"
    & ".\venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
    exit 0
}

$pythonCmd = "python"
if (-not (Get-Command "python" -ErrorAction SilentlyContinue)) {
    if (Get-Command "py" -ErrorAction SilentlyContinue) {
        $pythonCmd = "py"
    } else {
        Write-Host "[!] Python não foi encontrado no PATH do sistema." -ForegroundColor Red
        Write-Host "Instale o Python 3.10+ marcando 'Add Python to PATH' ou use docker-compose up." -ForegroundColor Yellow
        Read-Host "Pressione Enter para sair..."
        exit 1
    }
}

if (-not (Test-Path "venv")) {
    Write-Host "[*] Criando ambiente virtual venv..." -ForegroundColor Green
    & $pythonCmd -m venv venv
}

Write-Host "[*] Instalando dependências..." -ForegroundColor Green
& ".\venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet

Write-Host ""
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  🚀 Servidor iniciado! Acesse: http://localhost:8000" -ForegroundColor Green
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

Start-Process "http://localhost:8000"
& ".\venv\Scripts\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

