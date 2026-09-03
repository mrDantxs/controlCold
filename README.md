# ❄️ AntiGravity ColdChain (IoT Freezer & Cold Room Monitor)

Sistema centralizado para monitoramento de telemetria de temperatura e umidade em múltiplos freezers industriais e comerciais em tempo real. Desenvolvido para o ecossistema de sensores **Ekaza / Tuya (Wi-Fi e Zigbee)**, o sistema oferece prevenção ativa de perdas, gráficos de histórico, detecção de desvios térmicos e alarmes sonoros e via Telegram.

---

## 📱 Destaques da Solução

- **Interface Responsiva de Alta Performance**: Desenvolvida com design moderno em Glassmorphism, otimizada tanto para **smartphones** (visualização tátil, rápida e intuitiva) quanto para **telas de PC / monitores de controle** (painel executivo completo).
- **Backend em Python com TinyTuya + FastAPI**:
  - **Local LAN (TinyTuya)**: Leitura direta na rede local com resposta instantânea e funcionamento contínuo mesmo se a internet cair.
  - **Tuya Cloud OpenAPI v2.0**: Integração oficial com a nuvem Tuya usando `TUYA_ACCESS_ID` e `TUYA_ACCESS_SECRET`.
  - **Simulador Termodinâmico Realista**: Permite testar todo o sistema, curvas e alarmes de imediato sem necessidade de sensores físicos conectados.
- **Transmissão em Tempo Real**: Telemetria transmitida aos navegadores via **WebSockets** com atualização a cada 3 segundos e reconexão automática.
- **Motor de Prevenção de Perdas**:
  - Detecção imediata de violações dos limites mínimo e máximo configurados.
  - Alerta de aproximação preventiva.
  - Supressão de falso alarme e notificação automática de normalização (resolvido).
- **Notificações Críticas**: Disparo instantâneo via **Telegram Bot** e alarme sonoro sintetizado direto no navegador (com opção de silenciar).

---

## 🏗️ Estrutura do Projeto

```text
controlCold/
├── backend/
│   ├── src/
│   │   ├── collectors/
│   │   │   ├── tuya_client.py       # Integração Tuya Cloud e TinyTuya Local LAN
│   │   │   └── simulator.py         # Simulador termodinâmico para testes
│   │   ├── rules_engine/
│   │   │   └── evaluator.py         # Motor de regras térmicas e prevenção de perdas
│   │   ├── alerts/
│   │   │   └── telegram_bot.py      # Notificações no Telegram com formatação HTML
│   │   ├── database/
│   │   │   ├── models.py            # Modelos SQLAlchemy (Freezers, Logs, Alarmes)
│   │   │   └── db.py                # Banco assíncrono SQLite / PostgreSQL
│   │   └── api/
│   │       ├── routes.py            # Endpoints REST (CRUD de freezers, gráficos, testes)
│   │       └── websocket.py         # WebSocket Manager para push ao vivo
│   ├── Dockerfile
│   ├── requirements.txt
│   └── main.py                      # Servidor FastAPI e loop de coleta contínua
├── frontend/
│   ├── index.html                   # Interface Web moderna e semântica
│   ├── css/
│   │   └── styles.css               # Design System responsivo (Mobile e Desktop)
│   └── js/
│       ├── app.js                   # Controlador da aplicação
│       ├── socket.js                # Cliente WebSocket com alerta sonoro Web Audio
│       └── charts.js                # Gráficos dinâmicos com Chart.js
├── docker-compose.yml               # Execução em contêiner com 1 comando
├── iniciar.bat                      # Inicializador automático para Windows (1 clique)
├── iniciar.ps1                      # Inicializador PowerShell
├── .env.example                     # Modelo de variáveis de ambiente
└── README.md
```

---

## 🚀 Como Executar

### Opção 1: No Windows com 1 Clique (Recomendado)

Basta dar um duplo clique no arquivo:
```cmd
iniciar.bat
```
*O script criará o ambiente virtual Python (`venv`), instalará as bibliotecas necessárias e abrirá automaticamente o navegador em `http://localhost:8000`.*

---

### Opção 2: Via Terminal (Manual)

1. Entre na pasta do backend e crie o ambiente virtual:
   ```bash
   cd backend
   python -m venv venv
   ```
2. Ative o ambiente:
   - **Windows (CMD):** `venv\Scripts\activate`
   - **Windows (PowerShell):** `.\venv\Scripts\Activate.ps1`
   - **Linux / Mac:** `source venv/bin/activate`
3. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
4. Inicie o servidor:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000 --reload
   ```
5. Acesse no navegador:
   - **No PC:** `http://localhost:8000`
   - **No Celular:** Conecte na mesma rede Wi-Fi e acesse `http://<IP_DO_SEU_PC>:8000`

---

### Opção 3: Via Docker / Docker Compose

Se preferir rodar em contêiner isolado:
```bash
docker-compose up -d
```
O sistema subirá automaticamente com volume persistente na pasta `./data`.

---

## ⚙️ Configuração das Variáveis de Ambiente (`.env`)

Copie o arquivo `.env.example` para `.env` e ajuste suas chaves:

```ini
# Credenciais Tuya Cloud OpenAPI (platform.tuya.com)
TUYA_ENDPOINT=https://openapi.tuyaus.com
TUYA_ACCESS_ID=seu_access_id_aqui
TUYA_ACCESS_SECRET=seu_access_secret_aqui

# Limites Térmicos Padrão (°C)
FREEZER_CONGELADOS_MIN=-22.0
FREEZER_CONGELADOS_MAX=-15.0

# Alertas no Telegram
TELEGRAM_BOT_TOKEN=seu_bot_token_do_botfather
TELEGRAM_CHAT_ID=seu_chat_id

# Banco de Dados (deixe padrão para SQLite local automático)
DATABASE_URL=sqlite+aiosqlite:///coldchain.db
```

> **Nota sobre o Modo Simulação:**  
> Caso você ainda não tenha preenchido as credenciais Tuya reais ou seus sensores ainda não estejam ligados, o sistema ativa automaticamente o **Modo Simulação Inteligente**, populando 4 freezers com comportamentos térmicos realistas (`FRZ-01-SORVETES`, `FRZ-02-CARNES`, `FRZ-03-LATICINIOS` e `FRZ-04-VACINAS`). Isso permite que você avalie os gráficos, teste os alarmes sonoros e cadastre novos sensores imediatamente!

---

## 🛠️ Boas Práticas de Instalação Física do Sensor

1. **Gaiola de Faraday:** Freezers de inox e câmaras frigoríficas bloqueiam severamente o sinal Wi-Fi/Zigbee. Utilize sensores de temperatura com **sonda com fio à prova d'água**: a ponta da sonda fica dentro do freezer e o transmissor com antena e baterias fica no lado de fora.
2. **Vida Útil das Pilhas:** Pilhas comuns descarregam rapidamente se expostas a temperaturas de -20°C. Manter o transmissor no exterior preserva as baterias e evita congelamento.
3. **Nomenclatura no App:** Ao parear no Smart Life ou Ekaza, adote nomes padronizados como `FRZ-01-SORVETES`, facilitando a identificação no dashboard.