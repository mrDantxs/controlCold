# start.ps1
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "   Iniciando ControlCold (Docker + API)  " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Sobe o banco/serviços no Docker (se o Docker estiver instalado)
Write-Host "[*] Tentando iniciar os containers do Docker (pode ignorar se não tiver Docker)..." -ForegroundColor Yellow
try {
    docker compose up -d 2>$null
} catch {}

# 2. Entra na pasta do backend e ativa o ambiente
Write-Host "[*] Preparando o backend Python..." -ForegroundColor Yellow
Set-Location -Path "backend"

if (Test-Path "venv\Scripts\Activate.ps1") {
    . .\venv\Scripts\Activate.ps1
} else {
    Write-Host "[!] Ambiente virtual (venv) não encontrado! Rode o iniciar.bat uma vez primeiro." -ForegroundColor Red
    exit
}

# 2.5 Instala dependências novas (como pywebpush e reportlab)
Write-Host "[*] Instalando pacotes..." -ForegroundColor Yellow
pip install -r requirements.txt --quiet

# 3. Inicia o servidor uvicorn
Write-Host "[*] Iniciando o servidor Uvicorn..." -ForegroundColor Green
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
