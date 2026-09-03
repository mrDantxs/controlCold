@echo off
chcp 65001 > nul
title ControlCold - Monitor de Freezers IoT

echo ========================================================
echo   ❄️  ControlCold - Monitor de Freezers IoT
echo ========================================================
echo.

cd /d "%~dp0backend"

:: Se o venv já existe, pula direto para a ativação e inicialização
if exist "venv\Scripts\python.exe" (
    call venv\Scripts\activate
    goto start_server
)

:: 1. Tenta comando python direto
set PYTHON_CMD=python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    :: 2. Tenta comando py launcher
    py --version >nul 2>&1
    if %errorlevel% equ 0 (
        set PYTHON_CMD=py
    ) else (
        :: 3. Tenta caminhos comuns de instalação do Python (AppData / Program Files)
        if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
            set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        ) else if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" (
            set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        ) else if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" (
            set "PYTHON_CMD=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        ) else if exist "C:\Program Files\Python313\python.exe" (
            set "PYTHON_CMD=C:\Program Files\Python313\python.exe"
        ) else if exist "C:\Program Files\Python312\python.exe" (
            set "PYTHON_CMD=C:\Program Files\Python312\python.exe"
        ) else (
            echo [!] Python não foi encontrado no PATH do sistema.
            echo Por favor, instale o Python 3.10+ marcando a opção "Add Python to PATH"
            echo ou execute via Docker: docker-compose up -d
            pause
            exit /b 1
        )
    )
)

:: Cria ambiente virtual se não existir
if not exist "venv" (
    echo [*] Criando ambiente virtual Python (venv)...
    %PYTHON_CMD% -m venv venv
)

:: Ativa ambiente virtual
call venv\Scripts\activate

echo [*] Verificando e instalando dependências (FastAPI, TinyTuya, etc)...
pip install -r requirements.txt --quiet

:start_server
echo.
echo ========================================================
echo   🚀 Servidor iniciado com sucesso!
echo   📱 Acesso Web (PC e Celular): http://localhost:8000
echo ========================================================
echo.

start http://localhost:8000

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
pause
