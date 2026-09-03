# 🎯 Roadmap de Metas: AntiGravity ColdChain

## 🧠 1. Motor de Inteligência e Padrões Térmicos
- [x] Remover a dependência exclusiva de limites fixos e engessados (`FREEZER_CONGELADOS_MIN` e `FREEZER_CONGELADOS_MAX`) no script `evaluator.py`[cite: 1].
- [x] Implementar algoritmos preditivos (Inteligência Artificial) para mapear o comportamento térmico normal e aprender o ciclo específico de degelo de cada freezer[cite: 2].
- [x] Configurar o sistema para disparar alarmes apenas quando detectar variações genuinamente perigosas na temperatura, reduzindo falsos positivos[cite: 2].

## 📊 2. Conformidade, Auditoria e Relatórios
- [x] Expandir as tabelas do banco de dados no arquivo `models.py`[cite: 1] para armazenar logs de auditoria (ex: registro exato de qual usuário silenciou um alarme, a data/hora e o motivo).
- [x] Manter o monitoramento dinâmico via *Chart.js*[cite: 1], mas adicionar um módulo para exportação automatizada de dados.
- [x] Desenvolver a geração de relatórios de controle de qualidade em formato PDF imutável e rastreável, essenciais para fiscalizações sanitárias[cite: 2].

## 🏥 3. Calibração e Setor Farmacêutico
- [x] Adaptar o backend para suportar a inserção e o armazenamento de certificados de calibração individuais para cada sensor[cite: 2].
- [x] Desenvolver um sistema de "offsets" corretivos, aplicando ajustes matemáticos automáticos aos dados brutos recebidos da Tuya para garantir precisão rigorosa[cite: 2].

## 🔋 4. Frequência de Ingestão e Gestão de Bateria
- [x] Desativar a atualização agressiva de telemetria a cada 3 segundos[cite: 1], que drena rapidamente sensores IoT baseados em bateria.
- [x] Ajustar o polling ou webhook para realizar medições automáticas em intervalos conservadores (ex: a cada 5 a 10 minutos)[cite: 2].
- [x] Capturar o status de energia do hardware e implementar um alarme crítico de "bateria fraca".

## 📱 5. Plataforma e Aplicativo Nativo
- [ ] Evoluir a atual interface web responsiva (Glassmorphism)[cite: 1] para a arquitetura de um Aplicativo Nativo ou PWA configurado[cite: 2].
- [ ] Implementar um serviço de notificações Push diretas no smartphone do usuário para diminuir a dependência de serviços de terceiros, como o atual Telegram Bot[cite: 1].