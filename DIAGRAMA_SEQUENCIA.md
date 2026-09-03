# 📊 Diagrama de Sequência e Arquitetura - ControlCold

Este documento detalha o funcionamento interno de ponta a ponta do sistema **ControlCold**, demonstrando a camada de segurança e controle de acesso (login, cadastro com código de 6 dígitos, recuperação de senha) e o ciclo de vida dos dados de telemetria IoT.

---

## 🗺️ Visão Geral dos Módulos Envolvidos

1. **Camada de Segurança (`auth.py` / `auth_routes.py`)**: Autenticação, hash criptográfico PBKDF2, tokens assinados e motor de código de 6 dígitos.
2. **Hardware / Simulador**: Sensores Ekaza/Tuya ou Simulador Termodinâmico.
3. **Coletor de Telemetria (`tuya_client.py` / `simulator.py`)**: Realiza requisições LAN/Cloud ou gera medições físicas.
4. **Motor de Regras (`evaluator.py`)**: Analisa desvios de temperatura, histerese e supressão de alarmes.
5. **Banco de Dados Assíncrono (`db.py` / SQLite / PostgreSQL)**: Registra usuários, dispositivos, histórico de medições e incidentes.
6. **Central de Alertas (`telegram_bot.py`)**: Formata e envia mensagens para o smartphone dos operadores.
7. **Hub WebSocket & API REST (`websocket.py` / `routes.py`)**: Transmite dados ao vivo e responde requisições do frontend.
8. **Frontend Web (`index.html` / `app.js` / `socket.js` / `charts.js`)**: Renderiza visualizações táteis em smartphones e painel executivo em PCs.

---

## 1. 🔐 Fluxo de Autenticação e Login Seguro

Demonstra o acesso do administrador mestre (`willian.dantas@admin.com` / `98765432`) e operadores:

```mermaid
sequenceDiagram
    autonumber
    actor Usuario as 👤 Usuário / Administrador
    participant UI as 📱 Interface Web (app.js)
    participant AuthAPI as 🔒 Auth API (auth_routes.py)
    participant Sec as 🛡️ Security Engine (auth.py)
    participant DB as 🗄️ Database (models.py)

    Usuario->>UI: Informa e-mail (willian.dantas@admin.com) e senha (98765432)
    UI->>AuthAPI: POST /api/auth/login {email, password}
    activate AuthAPI
    AuthAPI->>DB: SELECT * FROM users WHERE email = 'willian.dantas@admin.com'
    DB-->>AuthAPI: Retorna registro do usuário
    
    AuthAPI->>Sec: verify_password(stored_hash, password)
    activate Sec
    Sec-->>AuthAPI: Senha Válida (True)
    deactivate Sec

    alt Conta não verificada
        AuthAPI->>Sec: generate_verification_code()
        Sec-->>AuthAPI: "582194"
        AuthAPI->>DB: UPDATE users SET verification_code='582194'
        AuthAPI->>Sec: send_email_verification(email, code)
        AuthAPI-->>UI: {requires_verification: true, message: "Digite o código enviado"}
        UI-->>Usuario: Exibe tela de digitação do código de 6 dígitos
    else Conta verificada (is_verified = True)
        AuthAPI->>Sec: create_auth_token(user.id, user.email, user.role)
        Sec-->>AuthAPI: Token de Acesso Assinado (JWT)
        AuthAPI-->>UI: {success: true, token, user}
        UI->>UI: Armazena token no localStorage e exibe perfil no cabeçalho
        UI-->>Usuario: Acesso liberado ao painel ControlCold!
    end
    deactivate AuthAPI
```

---

## 2. 📨 Fluxo de Cadastro com Verificação em 2 Etapas (Código de 6 Dígitos)

Todo novo usuário cadastrado com e-mail ou telefone deve obrigatoriamente confirmar o código recebido:

```mermaid
sequenceDiagram
    autonumber
    actor NovoUsuario as 👤 Novo Usuário
    participant UI as 📱 Interface Web
    participant AuthAPI as 🔒 Auth API (auth_routes.py)
    participant Sec as 🛡️ Security Engine (auth.py)
    participant DB as 🗄️ Database
    participant Email as 📧 Serviço de Email / SMS

    %% Etapa 1: Cadastro
    NovoUsuario->>UI: Preenche E-mail, Telefone e Senha
    UI->>AuthAPI: POST /api/auth/register {email, phone, password}
    activate AuthAPI
    AuthAPI->>Sec: hash_password(password)
    AuthAPI->>Sec: generate_verification_code()
    Sec-->>AuthAPI: Código "741852" (válido por 15 min)
    
    AuthAPI->>DB: INSERT INTO users (email, phone, pwd_hash, is_verified=False, verification_code='741852')
    DB-->>AuthAPI: Salvo com sucesso
    
    AuthAPI->>Sec: send_email_verification(email, '741852')
    Sec->>Email: Dispara mensagem com o código de 6 dígitos
    AuthAPI-->>UI: {success: true, message: "Código enviado", dev_code: "741852"}
    deactivate AuthAPI
    UI-->>NovoUsuario: Abre modal solicitando os 6 dígitos

    %% Etapa 2: Confirmação
    NovoUsuario->>UI: Digita os 6 dígitos recebidos (741852)
    UI->>AuthAPI: POST /api/auth/verify {email, code: "741852"}
    activate AuthAPI
    AuthAPI->>DB: SELECT * FROM users WHERE email = ...
    alt Código confere e não expirou
        AuthAPI->>DB: UPDATE users SET is_verified = True, verification_code = NULL
        AuthAPI->>Sec: create_auth_token(user.id, user.email, user.role)
        Sec-->>AuthAPI: Token gerado
        AuthAPI-->>UI: {success: true, token, user}
        UI-->>NovoUsuario: Conta ativada com sucesso! Redireciona para o painel.
    else Código incorreto ou expirado
        AuthAPI-->>UI: 400 Bad Request ("Código incorreto ou expirado")
        UI-->>NovoUsuario: Exibe mensagem de erro
    end
    deactivate AuthAPI
```

---

## 3. 🔑 Fluxo de Recuperação e Redefinição de Senha

Processo seguro para redefinir senha sem expor credenciais:

```mermaid
sequenceDiagram
    autonumber
    actor Usuario as 👤 Usuário
    participant UI as 📱 Interface Web
    participant AuthAPI as 🔒 Auth API (auth_routes.py)
    participant Sec as 🛡️ Security Engine (auth.py)
    participant DB as 🗄️ Database

    Usuario->>UI: Clica em "Esqueci minha senha" e informa o e-mail
    UI->>AuthAPI: POST /api/auth/forgot-password {email}
    activate AuthAPI
    AuthAPI->>Sec: generate_verification_code()
    Sec-->>AuthAPI: Código "963258"
    AuthAPI->>DB: UPDATE users SET verification_code='963258', expires_at=NOW()+15m
    AuthAPI->>Sec: send_email_verification(email, '963258', 'recuperação de senha')
    AuthAPI-->>UI: {message: "Código de recuperação enviado", dev_code: "963258"}
    deactivate AuthAPI
    UI-->>Usuario: Exibe tela de redefinição de senha

    Usuario->>UI: Digita o código (963258) e a nova senha desejada
    UI->>AuthAPI: POST /api/auth/reset-password {email, code, new_password}
    activate AuthAPI
    AuthAPI->>DB: Valida código e expiração
    AuthAPI->>Sec: hash_password(new_password)
    AuthAPI->>DB: UPDATE users SET password_hash=..., verification_code=NULL
    AuthAPI-->>UI: {success: true, message: "Senha redefinida com sucesso!"}
    deactivate AuthAPI
    UI-->>Usuario: Notifica sucesso e direciona para a tela de login
```

---

## 4. 🔄 Fluxo de Inicialização do Sistema (Startup & Lifespan)

Quando o servidor é iniciado, ele prepara as tabelas, cadastra o administrador e inicia o monitoramento térmico:

```mermaid
sequenceDiagram
    autonumber
    actor Operador as 👤 Operador / Sistema
    participant Main as 🚀 backend/main.py
    participant DB as 🗄️ Database (SQLite/Postgres)
    participant SeedAdmin as 👑 Seeder Administrador
    participant SeedDev as 🌱 Seeder Freezers
    participant Loop as ⏱️ Background Telemetry Loop

    Operador->>Main: Inicia servidor (uvicorn main:app)
    activate Main
    Main->>DB: init_db() -> Cria tabelas (users, devices, telemetry_logs, alarm_events)
    DB-->>Main: Tabelas verificadas/prontas
    
    Main->>SeedAdmin: seed_admin_user()
    activate SeedAdmin
    SeedAdmin->>DB: Verifica willian.dantas@admin.com
    alt Se administrador não existir
        SeedAdmin->>DB: INSERT administrador com senha criptografada 98765432
        DB-->>SeedAdmin: Administrador criado
    end
    deactivate SeedAdmin

    Main->>SeedDev: seed_initial_devices_if_empty()
    activate SeedDev
    SeedDev->>DB: SELECT COUNT(*) FROM devices
    alt Se banco de freezers estiver vazio
        SeedDev->>DB: INSERT freezers padrão (Sorvetes, Carnes, Laticínios, Vacinas)
        DB-->>SeedDev: Freezers cadastrados
    end
    deactivate SeedDev

    Main->>Loop: asyncio.create_task(telemetry_collection_loop())
    activate Loop
    Main-->>Operador: Servidor pronto na porta 8000 (HTTP + WebSocket)
    deactivate Main
```

---

## 5. 📡 Fluxo de Coleta Periódica e Telemetria em Tempo Real

A cada **3 segundos**, o loop em segundo plano consulta os equipamentos, processa as leituras e transmite para os navegadores conectados:

```mermaid
sequenceDiagram
    autonumber
    participant Loop as ⏱️ Background Loop (main.py)
    participant DB as 🗄️ Database (db.py)
    participant Tuya as 🔌 TuyaClient (tuya_client.py)
    participant Sim as 🧪 TelemetrySimulator (simulator.py)
    participant Rules as 🧠 RulesEngine (evaluator.py)
    participant WS as ⚡ WebSocket Manager
    participant Frontend as 📱 Frontend ControlCold (Mobile/PC)

    loop A cada 3 segundos
        Loop->>DB: SELECT * FROM devices WHERE is_active = True
        DB-->>Loop: Lista de freezers cadastrados
        
        loop Para cada Freezer
            alt Se Tuya Cloud/LAN estiver configurado
                Loop->>Tuya: read_device_local() ou get_device_status()
                Tuya-->>Loop: {temp, hum, battery}
            else Modo Simulação Ativo (Fallback)
                Loop->>Sim: generate_reading(device_config)
                Sim-->>Loop: {temp, hum, battery}
            end

            Loop->>Rules: evaluate(device, temp, temp_min, temp_max, battery)
            Rules-->>Loop: (status, new_alarms, resolved_alarms)

            Loop->>DB: INSERT TelemetryLog & UPDATE Device (current_temp, status)
            DB-->>Loop: Persistido

            Loop->>WS: broadcast("TELEMETRY_UPDATE", payload)
            WS-->>Frontend: Envia atualização via WebSocket sem recarregar a tela
            Frontend->>Frontend: Atualiza dígitos gigantes, barra do termômetro e gráfico
        end
    end
```

---

## 6. 🚨 Fluxo de Detecção de Violação Térmica e Disparo de Alarme

Caso um freezer ultrapasse a temperatura limite (ex: porta esquecida aberta ou compressor desligado):

```mermaid
sequenceDiagram
    autonumber
    participant Loop as ⏱️ Background Loop
    participant Rules as 🧠 RulesEngine (evaluator.py)
    participant DB as 🗄️ Database
    participant Telegram as ✈️ TelegramNotifier
    participant WS as ⚡ WebSocket Manager
    participant Frontend as 📱 Frontend (Navegador)
    actor Operador as 👤 Operador

    Note over Loop,Rules: Temperatura sobe para -13.5°C (Limite Máx: -15.0°C)
    Loop->>Rules: evaluate(temp=-13.5, temp_max=-15.0)
    activate Rules
    Rules->>Rules: Detecta violação: status = CRITICO
    Rules->>Rules: Verifica se alarme TEMP_HIGH já está ativo (Anti-Spam)
    Rules-->>Loop: Retorna new_alarms=[{device, severity: CRITICAL, message: "🚨..."}]
    deactivate Rules

    Loop->>DB: INSERT AlarmEvent (status: ACTIVE)
    
    par Notificação no Smartphone (Telegram)
        Loop->>Telegram: send_alarm(alarm_data)
        Telegram->>Operador: Mensagem Push com emoji 🚨, equipamento, medição e limites
    and Transmissão ao Vivo aos Navegadores
        Loop->>WS: broadcast("NEW_ALARM", alarm_data)
        WS-->>Frontend: Mensagem WebSocket do tipo NEW_ALARM
        Frontend->>Frontend: 1. Aciona sintetizador sonoro Web Audio (Bipe de Alarme)
        Frontend->>Frontend: 2. Exibe faixa vermelha pulsante no topo da tela
        Frontend->>Frontend: 3. Adiciona linha na tabela de ocorrências recentes
    end
```

---

## 7. ✅ Fluxo de Normalização da Temperatura (Resolução do Incidente)

Quando a porta do freezer é fechada e o compressor restabelece a temperatura segura:

```mermaid
sequenceDiagram
    autonumber
    participant Loop as ⏱️ Background Loop
    participant Rules as 🧠 RulesEngine (evaluator.py)
    participant DB as 🗄️ Database
    participant Telegram as ✈️ TelegramNotifier
    participant WS as ⚡ WebSocket Manager
    participant Frontend as 📱 Frontend

    Note over Loop,Rules: Temperatura desce para -18.2°C (Faixa Segura: -22 a -15°C)
    Loop->>Rules: evaluate(temp=-18.2)
    activate Rules
    Rules->>Rules: Identifica que alarme TEMP_HIGH foi sanado
    Rules-->>Loop: resolved_alarms=["TEMP_HIGH"], status = NORMAL
    deactivate Rules

    Loop->>DB: UPDATE AlarmEvent SET status='RESOLVED', resolved_at=NOW()
    
    par Encerramento no Telegram
        Loop->>Telegram: send_resolution(device_name, current_temp)
        Telegram-->>Operador: Notificação: "✅ [RESOLVIDO] Temperatura Normalizada"
    and Encerramento no Frontend
        Loop->>WS: broadcast("ALARM_RESOLVED", payload)
        WS-->>Frontend: Remove faixa crítica e atualiza badge para NORMAL
    end
```

---

## 8. 👆 Fluxo de Interação do Usuário (Frontend Mobile & Desktop)

Como as interações na interface (ajuste de limites, visualização de gráfico e testes) são processadas:

```mermaid
sequenceDiagram
    autonumber
    actor Usuario as 👤 Usuário (Mobile / PC)
    participant UI as 📱 Interface Web (app.js)
    participant API as 🌐 REST API (routes.py)
    participant DB as 🗄️ Database
    participant Chart as 📈 Chart.js Manager

    %% Caso 1: Ver Histórico
    Usuario->>UI: Clica em "📊 Gráfico" no Card do Freezer
    UI->>API: GET /api/devices/{id}/history?limit=40
    API->>DB: SELECT * FROM telemetry_logs ORDER BY timestamp DESC
    DB-->>API: Registros históricos
    API-->>UI: Array JSON de temperaturas e umidades
    UI->>Chart: render(logs, device)
    UI-->>Usuario: Abre modal com curva suave e limites min/max destacados

    %% Caso 2: Ajuste de Limites
    Usuario->>UI: Clica em "⚙️ Limites" e altera temp_max para -14.0°C
    Usuario->>UI: Clica em "Salvar Freezer"
    UI->>API: PUT /api/devices/{id} {"temp_max": -14.0}
    API->>DB: UPDATE devices SET temp_max = -14.0
    DB-->>API: Salvo com sucesso
    API-->>UI: Dispositivo atualizado
    UI-->>Usuario: Fecha modal e atualiza réguas do termômetro instantaneamente

    %% Caso 3: Teste de Alarme Simulado
    Usuario->>UI: Clica em "⚡ Testar Alarme / Spike"
    UI->>API: POST /api/system/simulate-incident {"device_id": "...", "anomaly_type": "DOOR_OPEN"}
    API-->>UI: Anomalia ativada
    Note over UI: Em 3s a curva sobe, o alarme sonoro toca e o banner vermelho surge!
```

---

## 📑 Resumo dos Protocolos e Portas

| Comunicação | Protocolo | Origem | Destino | Finalidade |
| :--- | :--- | :--- | :--- | :--- |
| **Autenticação** | HTTPS REST (PBKDF2/Tokens) | Frontend | `/api/auth/*` | Login, registro, 6 dígitos e recuperação |
| **Leitura Local** | UDP/TCP (Tuya 3.3/3.4) | Backend | Sensor / Gateway Ekaza | Leitura direta sem internet |
| **Nuvem Tuya** | HTTPS REST (HMAC-SHA256) | Backend | `openapi.tuyaus.com` | Leitura via Tuya Developer Cloud |
| **Streaming Web** | WebSocket (`ws://`) | Frontend | `backend/ws/live` | Atualização instantânea a cada 3s |
| **API REST** | HTTP (`http://`) | Frontend | `backend/api/*` | CRUD, histórico, limites e overview |
| **Alertas Push** | HTTPS REST | Backend | `api.telegram.org` | Envio de mensagens e avisos críticos |
| **Confirmação Email**| SMTP / TLS (Porta 587) | Backend | Provedor de Email | Envio de código de 6 dígitos |
