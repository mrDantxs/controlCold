/**
 * ControlCold - Aplicação Principal Frontend
 * Portal de Segurança com Verificação em Duas Etapas (Código de 6 Dígitos)
 */

document.addEventListener('DOMContentLoaded', () => {
    // Estado da Aplicação
    const state = {
        devices: [],
        alarms: [],
        overview: {},
        activeFilter: 'all',
        selectedDevice: null,
        soundEnabled: true,
        isDarkTheme: true,
        currentUser: null,
        refreshToken: localStorage.getItem('controlcold_refresh') || null,
        pendingEmailForVerify: '',
        lastDevCode: '',
        currentAuthView: 'login',
        refreshIntervals: []
    };

    // Elementos do DOM
    const dom = {
        // Telas Principais
        authPortalScreen: document.getElementById('authPortalScreen'),
        dashboardScreen: document.getElementById('dashboardScreen'),

        // Elementos do Portal de Autenticação
        authViewLogin: document.getElementById('authViewLogin'),
        authViewRegister: document.getElementById('authViewRegister'),
        authViewVerify: document.getElementById('authViewVerify'),
        authViewForgot: document.getElementById('authViewForgot'),
        authViewReset: document.getElementById('authViewReset'),

        loginForm: document.getElementById('loginForm'),
        loginEmail: document.getElementById('loginEmail'),
        loginPassword: document.getElementById('loginPassword'),
        toRegisterBtn: document.getElementById('toRegisterBtn'),
        toForgotBtn: document.getElementById('toForgotBtn'),

        registerForm: document.getElementById('registerForm'),
        regEmail: document.getElementById('regEmail'),
        regPhone: document.getElementById('regPhone'),
        regPassword: document.getElementById('regPassword'),
        backToLoginBtn: document.getElementById('backToLoginBtn'),

        verifyForm: document.getElementById('verifyForm'),
        verifyTargetEmail: document.getElementById('verifyTargetEmail'),
        inputVerifyCode: document.getElementById('inputVerifyCode'),
        resendCodeBtn: document.getElementById('resendCodeBtn'),

        forgotForm: document.getElementById('forgotForm'),
        forgotEmail: document.getElementById('forgotEmail'),
        forgotBackToLoginBtn: document.getElementById('forgotBackToLoginBtn'),

        resetForm: document.getElementById('resetForm'),
        resetCode: document.getElementById('resetCode'),
        resetNewPassword: document.getElementById('resetNewPassword'),

        // Elementos do Painel de Monitoramento
        navUserEmail: document.getElementById('navUserEmail'),
        logoutBtn: document.getElementById('logoutBtn'),
        liveStatusBadge: document.getElementById('liveStatusBadge'),
        liveStatusText: document.getElementById('liveStatusText'),
        soundToggleBtn: document.getElementById('soundToggleBtn'),
        soundIcon: document.getElementById('soundIcon'),
        themeToggleBtn: document.getElementById('themeToggleBtn'),
        themeIcon: document.getElementById('themeIcon'),
        systemInfoBtn: document.getElementById('systemInfoBtn'),

        // KPIs
        valTotalDevices: document.getElementById('valTotalDevices'),
        valNormalDevices: document.getElementById('valNormalDevices'),
        valAlertDevices: document.getElementById('valAlertDevices'),
        valCriticalDevices: document.getElementById('valCriticalDevices'),
        valAvgTemp: document.getElementById('valAvgTemp'),
        valSystemMode: document.getElementById('valSystemMode'),

        // Alertas e Grid
        activeAlarmsBanner: document.getElementById('activeAlarmsBanner'),
        alarmBannerTitle: document.getElementById('alarmBannerTitle'),
        alarmBannerDesc: document.getElementById('alarmBannerDesc'),
        silenceAlarmBannerBtn: document.getElementById('silenceAlarmBannerBtn'),
        devicesGrid: document.getElementById('devicesGrid'),
        alarmsTableBody: document.getElementById('alarmsTableBody'),
        alarmCountBadge: document.getElementById('alarmCountBadge'),

        // Ações Rápidas
        addDeviceBtn: document.getElementById('addDeviceBtn'),
        testSimulationBtn: document.getElementById('testSimulationBtn'),

        // Modais de Controle
        chartModal: document.getElementById('chartModal'),
        deviceModal: document.getElementById('deviceModal'),
        systemModal: document.getElementById('systemModal'),
        
        closeChartModalBtn: document.getElementById('closeChartModalBtn'),
        closeChartModalFooterBtn: document.getElementById('closeChartModalFooterBtn'),
        closeDeviceModalBtn: document.getElementById('closeDeviceModalBtn'),
        cancelDeviceModalBtn: document.getElementById('cancelDeviceModalBtn'),
        closeSystemModalBtn: document.getElementById('closeSystemModalBtn'),
        closeSystemModalFooterBtn: document.getElementById('closeSystemModalFooterBtn'),

        // Formulário de Dispositivo
        deviceForm: document.getElementById('deviceForm'),
        deviceModalTitle: document.getElementById('deviceModalTitle'),
        editDeviceId: document.getElementById('editDeviceId'),
        inputDeviceId: document.getElementById('inputDeviceId'),
        inputDeviceName: document.getElementById('inputDeviceName'),
        inputCategory: document.getElementById('inputCategory'),
        inputLocation: document.getElementById('inputLocation'),
        inputTempMin: document.getElementById('inputTempMin'),
        inputTempMax: document.getElementById('inputTempMax'),
        inputCalibrationCert: document.getElementById('inputCalibrationCert'),
        inputTempOffset: document.getElementById('inputTempOffset'),
        inputLocalIp: document.getElementById('inputLocalIp'),
        inputLocalKey: document.getElementById('inputLocalKey'),
        editLimitsFromChartBtn: document.getElementById('editLimitsFromChartBtn'),

        // Modal Gráfico
        modalDeviceTitle: document.getElementById('modalDeviceTitle'),
        modalDeviceSubtitle: document.getElementById('modalDeviceSubtitle'),
        modalCurrentTemp: document.getElementById('modalCurrentTemp'),
        modalTempLimits: document.getElementById('modalTempLimits'),
        modalHumidity: document.getElementById('modalHumidity'),
        modalBattery: document.getElementById('modalBattery'),

        // Modal Sistema
        sysStatusMode: document.getElementById('sysStatusMode'),
        sysStatusTuya: document.getElementById('sysStatusTuya'),
        sysStatusTelegram: document.getElementById('sysStatusTelegram'),
        testChatId: document.getElementById('testChatId'),
        sendTelegramTestBtn: document.getElementById('sendTelegramTestBtn'),
        telegramTestResult: document.getElementById('telegramTestResult'),
        
        // Ekaza Integration


        // Auditoria & Relatórios
        reportBtn: document.getElementById('reportBtn'),
        auditModal: document.getElementById('auditModal'),
        closeAuditModalBtn: document.getElementById('closeAuditModalBtn'),
        cancelAuditBtn: document.getElementById('cancelAuditBtn'),
        confirmAuditBtn: document.getElementById('confirmAuditBtn'),
        auditReason: document.getElementById('auditReason'),
        auditCustomReason: document.getElementById('auditCustomReason')
    };

    // Gerenciador de Gráficos
    const chartManager = new TelemetryChartManager('telemetryChart');

    // Gerenciador WebSocket com ciclo de vida controlado
    const socket = new RealtimeSocket({
        onTelemetryUpdate: (data) => handleTelemetryUpdate(data),
        onNewAlarm: (alarm) => handleNewAlarm(alarm),
        onAlarmResolved: (res) => handleAlarmResolved(res),
        onConnectionChange: (online) => updateConnectionStatus(online),
        onPollingTick: () => fetchDevices(false)
    });

    // Utilitário para chamadas autenticadas
    async function secureFetch(url, options = {}) {
        options.headers = options.headers || {};
        options.credentials = 'include'; // Permite envio de Cookies HttpOnly
        let res = await fetch(url, options);
        if (res.status === 401) {
            if (state.refreshToken && !options._retry) {
                options._retry = true;
                try {
                    const refreshRes = await fetch('/api/auth/refresh', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ refresh_token: state.refreshToken })
                    });
                    if (refreshRes.ok) {
                        const refreshData = await refreshRes.json();
                        return await fetch(url, options);
                    }
                } catch(e) {
                    console.error("Refresh token error", e);
                }
            }
            // Se o usuário estava autenticado e o token expirou (e o refresh falhou), desloga com segurança
            if (state.currentUser) {
                handleLogout(false);
            }
            throw new Error('Sessão expirada ou não autorizada.');
        }
        return res;
    }

    // -------------------------------------------------------------
    // Controle de Telas (Portal de Autenticação vs Painel de Monitoramento)
    // -------------------------------------------------------------
    function showAuthPortal(keepView = false) {
        dom.authPortalScreen.classList.remove('hidden');
        dom.dashboardScreen.classList.add('hidden');
        clearPeriodicRefresh();
        socket.stop();

        if (!keepView) {
            switchAuthView('login');
        }
    }

    function showDashboard() {
        dom.authPortalScreen.classList.add('hidden');
        dom.dashboardScreen.classList.remove('hidden');
        dom.navUserEmail.textContent = state.currentUser ? state.currentUser.email : 'Usuário';

        // Inicia coleta e WebSocket apenas após login com sucesso
        socket.start();
        fetchOverview();
        fetchDevices();
        fetchAlarms();
        startPeriodicRefresh();
        initPushNotifications();
    }

    function switchAuthView(viewName) {
        state.currentAuthView = viewName;
        [dom.authViewLogin, dom.authViewRegister, dom.authViewVerify, dom.authViewForgot, dom.authViewReset].forEach(v => {
            if (v) v.classList.add('hidden');
        });

        if (viewName === 'login') dom.authViewLogin.classList.remove('hidden');
        if (viewName === 'register') dom.authViewRegister.classList.remove('hidden');
        if (viewName === 'verify') dom.authViewVerify.classList.remove('hidden');
        if (viewName === 'forgot') dom.authViewForgot.classList.remove('hidden');
        if (viewName === 'reset') dom.authViewReset.classList.remove('hidden');
    }

    async function handleLogout(callApi = true) {
        if (callApi && state.refreshToken) {
            try {
                await fetch('/api/auth/logout', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ refresh_token: state.refreshToken })
                });
            } catch(e) {}
        }
        state.currentUser = null;
        state.authToken = null;
        state.refreshToken = null;
        localStorage.removeItem('controlcold_refresh');
        showAuthPortal();
    }

    // -------------------------------------------------------------
    // Fluxos de Autenticação e Registro com Verificação de 6 Dígitos
    // -------------------------------------------------------------
    // 1. Envio do Formulário de Login
    dom.loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = dom.loginEmail.value.trim();
        const password = dom.loginPassword.value;
        const submitBtn = document.getElementById('loginSubmitBtn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Verificando...';

        try {
            const res = await fetch('/api/auth/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password })
            });
            const data = await res.json();

            if (!res.ok) {
                alert(data.detail || 'E-mail ou senha incorretos.');
                return;
            }

            // Caso o e-mail não tenha sido verificado ainda
            if (data.requires_verification) {
                state.pendingEmailForVerify = data.email;
                dom.verifyTargetEmail.textContent = data.email;
                switchAuthView('verify');
                alert(data.message);
                return;
            }

            // Login bem-sucedido
            state.currentUser = data.user;
            if (data.refresh_token) {
                state.refreshToken = data.refresh_token;
                localStorage.setItem('controlcold_refresh', data.refresh_token);
            }

            showDashboard();
        } catch (err) {
            alert('Falha na comunicação com o servidor.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Entrar no Sistema';
        }
    });

    // 2. Envio do Formulário de Cadastro (Gera código de 6 dígitos)
    dom.registerForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = dom.regEmail.value.trim();
        const phone = dom.regPhone.value.trim();
        const password = dom.regPassword.value;
        const submitBtn = document.getElementById('registerSubmitBtn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Gerando Código...';

        try {
            const res = await fetch('/api/auth/register', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, phone, password })
            });
            const data = await res.json();

            if (!res.ok) {
                alert(data.detail || 'Falha ao cadastrar conta.');
                return;
            }

            // Guarda o e-mail que aguarda verificação
            state.pendingEmailForVerify = data.email;
            dom.verifyTargetEmail.textContent = data.email;
            dom.inputVerifyCode.value = '';

            // Muda para a tela de verificação e mantém fixo sem nenhum timer para fechar!
            switchAuthView('verify');
            alert(data.message);
        } catch (err) {
            alert('Erro ao realizar cadastro. Tente novamente.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Cadastrar & Receber Código';
        }
    });

    // 3. Validação do Código de 6 Dígitos (Somente libera após sucesso!)
    dom.verifyForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const code = dom.inputVerifyCode.value.trim();
        const email = state.pendingEmailForVerify;
        
        if (!code || code.length !== 6) {
            alert('Por favor, informe os 6 dígitos do código de confirmação.');
            return;
        }

        const submitBtn = document.getElementById('verifySubmitBtn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Validando Código...';

        try {
            const res = await fetch('/api/auth/verify', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, code })
            });
            const data = await res.json();

            if (!res.ok) {
                alert(data.detail || 'Código incorreto ou expirado. Verifique e tente novamente.');
                return;
            }

            // Sucesso! A conta agora está verificada
            state.currentUser = data.user;
            if (data.refresh_token) {
                state.refreshToken = data.refresh_token;
                localStorage.setItem('controlcold_refresh', data.refresh_token);
            }
            alert('Conta ativada e verificada com sucesso! Liberando acesso ao monitoramento.');
            showDashboard();
        } catch (err) {
            alert('Erro ao validar código com o servidor.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Confirmar & Ativar Conta';
        }
    });

    // 4. Solicitação de Recuperação de Senha
    dom.forgotForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = dom.forgotEmail.value.trim();
        const submitBtn = document.getElementById('forgotSubmitBtn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Enviando...';

        try {
            const res = await fetch('/api/auth/forgot-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email })
            });
            const data = await res.json();

            state.pendingEmailForVerify = email;
            switchAuthView('reset');
            alert(data.message);
        } catch (err) {
            alert('Erro ao solicitar recuperação.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Enviar Código de Recuperação';
        }
    });

    // 5. Redefinição de Senha com o Código
    dom.resetForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const code = dom.resetCode.value.trim();
        const new_password = dom.resetNewPassword.value;
        const email = state.pendingEmailForVerify;
        const submitBtn = document.getElementById('resetSubmitBtn');
        submitBtn.disabled = true;
        submitBtn.textContent = 'Salvando...';

        try {
            const res = await fetch('/api/auth/reset-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, code, new_password })
            });
            const data = await res.json();

            if (!res.ok) {
                alert(data.detail || 'Falha ao redefinir senha.');
                return;
            }

            switchAuthView('login');
            alert(data.message);
        } catch (err) {
            alert('Erro ao redefinir senha.');
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Salvar Nova Senha';
        }
    });

    // Navegação entre Telas de Autenticação
    dom.toRegisterBtn.addEventListener('click', () => switchAuthView('register'));
    dom.backToLoginBtn.addEventListener('click', () => switchAuthView('login'));
    dom.toForgotBtn.addEventListener('click', () => switchAuthView('forgot'));
    dom.forgotBackToLoginBtn.addEventListener('click', () => switchAuthView('login'));

    dom.logoutBtn.addEventListener('click', () => handleLogout(true));

    // Reenvio de Código de Verificação
    dom.resendCodeBtn.addEventListener('click', async () => {
        if (!state.pendingEmailForVerify) {
            switchAuthView('register');
            return;
        }
        dom.resendCodeBtn.textContent = 'Reenviando...';
        try {
            const res = await fetch('/api/auth/forgot-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email: state.pendingEmailForVerify })
            });
            const data = await res.json();
            alert('Um novo código de 6 dígitos foi enviado!');
        } catch (e) {
            alert('Não foi possível reenviar o código.');
        } finally {
            dom.resendCodeBtn.textContent = 'Reenviar Código';
        }
    });

    // -------------------------------------------------------------
    // Inicialização da Sessão
    // -------------------------------------------------------------
    async function initSession() {
        try {
            const res = await secureFetch('/api/auth/me', {
                method: 'GET'
            });
            if (res.ok) {
                state.currentUser = await res.json();
                showDashboard();
            } else {
                showAuthPortal(false);
            }
        } catch (e) {
            showAuthPortal(false);
        }
    }

    // -------------------------------------------------------------
    // Rotinas do Painel de Monitoramento (Somente ativas autenticado)
    // -------------------------------------------------------------
    function startPeriodicRefresh() {
        clearPeriodicRefresh();
        state.refreshIntervals.push(setInterval(fetchOverview, 6000));
        state.refreshIntervals.push(setInterval(fetchAlarms, 8000));
    }

    function clearPeriodicRefresh() {
        state.refreshIntervals.forEach(id => clearInterval(id));
        state.refreshIntervals = [];
    }

    async function fetchOverview() {
        if (!state.authToken) return;
        try {
            const res = await secureFetch('/api/overview');
            if (res.ok) {
                state.overview = await res.json();
                renderOverview();
            }
        } catch (e) {
            console.error('Erro overview:', e);
        }
    }

    async function fetchDevices(renderLoading = true) {
        if (!state.authToken) return;
        if (renderLoading && state.devices.length === 0) {
            dom.devicesGrid.innerHTML = `
                <div class="loading-state">
                    <div class="spinner"></div>
                    <p>Sincronizando sensores e telemetria segura...</p>
                </div>
            `;
        }
        try {
            const res = await secureFetch('/api/devices');
            if (res.ok) {
                state.devices = await res.json();
                renderDevicesGrid();
                updateActiveAlarmsBanner();
            }
        } catch (e) {
            console.error('Erro devices:', e);
        }
    }

    async function fetchAlarms() {
        if (!state.authToken) return;
        try {
            const res = await secureFetch('/api/alarms?limit=30');
            if (res.ok) {
                state.alarms = await res.json();
                renderAlarmsTable();
            }
        } catch (e) {
            console.error('Erro alarms:', e);
        }
    }

    function handleTelemetryUpdate(update) {
        const device = state.devices.find(d => d.id === update.device_id);
        if (device) {
            device.current_temp = update.temperature;
            device.current_humidity = update.humidity;
            device.battery_level = update.battery;
            device.status = update.status;
            device.last_seen = update.timestamp;

            updateCardElement(device);
            updateKpisFromState();

            if (state.selectedDevice && state.selectedDevice.id === device.id) {
                chartManager.appendReading(update);
                if (dom.modalCurrentTemp) dom.modalCurrentTemp.textContent = `${update.temperature.toFixed(1)} °C`;
                if (dom.modalHumidity) dom.modalHumidity.textContent = update.humidity ? `${update.humidity.toFixed(1)} %` : '-- %';
                if (dom.modalBattery) dom.modalBattery.textContent = `${update.battery}%`;
            }
        } else {
            fetchDevices(false);
        }
    }

    function handleNewAlarm(alarm) {
        state.alarms.unshift(alarm);
        renderAlarmsTable();
        updateActiveAlarmsBanner();

        if (alarm.severity === 'CRITICAL') {
            dom.activeAlarmsBanner.classList.remove('hidden');
            dom.alarmBannerTitle.textContent = `🚨 ALERTA CRÍTICO: ${alarm.device_name || alarm.device_id}`;
            dom.alarmBannerDesc.textContent = alarm.message;
        }
    }

    function handleAlarmResolved(resolution) {
        const matching = state.alarms.find(a => a.device_id === resolution.device_id && a.alarm_type === resolution.alarm_type && a.status === 'ACTIVE');
        if (matching) {
            matching.status = 'RESOLVED';
            renderAlarmsTable();
        }
        updateActiveAlarmsBanner();
    }

    function updateConnectionStatus(isOnline) {
        if (isOnline) {
            dom.liveStatusBadge.style.display = 'flex';
            dom.liveStatusText.textContent = 'AO VIVO';
        } else {
            dom.liveStatusText.textContent = 'RECONECTANDO';
        }
    }

    function renderOverview() {
        const o = state.overview;
        dom.valTotalDevices.textContent = o.total_devices ?? '--';
        dom.valNormalDevices.textContent = o.normal_count ?? '--';
        dom.valAlertDevices.textContent = o.alert_count ?? '--';
        dom.valCriticalDevices.textContent = o.critical_count ?? '--';
        dom.valAvgTemp.textContent = o.average_temp !== undefined ? `${o.average_temp.toFixed(1)} °C` : '-- °C';
        dom.valSystemMode.textContent = o.system_mode === 'LIVE_TUYA' ? 'Modo: Tuya Hardware' : 'Modo: Simulação IoT';

        dom.sysStatusMode.textContent = o.system_mode || '--';
        dom.sysStatusMode.className = `badge ${o.system_mode === 'LIVE_TUYA' ? 'status-NORMAL' : ''}`;
        dom.sysStatusTuya.textContent = o.tuya_configured ? 'Conectado (API OK)' : 'Aguardando Credenciais Reais';
        dom.sysStatusTelegram.textContent = o.telegram_configured ? 'Ativo' : 'Não Configurado';
    }

    function updateKpisFromState() {
        const total = state.devices.length;
        const normal = state.devices.filter(d => d.status === 'NORMAL').length;
        const alert = state.devices.filter(d => d.status === 'ALERTA').length;
        const critical = state.devices.filter(d => d.status === 'CRITICO').length;

        const temps = state.devices.map(d => d.current_temp).filter(t => t !== null && t !== undefined);
        const avg = temps.length > 0 ? (temps.reduce((a, b) => a + b, 0) / temps.length) : 0;

        dom.valTotalDevices.textContent = total;
        dom.valNormalDevices.textContent = normal;
        dom.valAlertDevices.textContent = alert;
        dom.valCriticalDevices.textContent = critical;
        dom.valAvgTemp.textContent = `${avg.toFixed(1)} °C`;
    }

    function updateActiveAlarmsBanner() {
        const criticalDevices = state.devices.filter(d => d.status === 'CRITICO');
        if (criticalDevices.length > 0) {
            const first = criticalDevices[0];
            dom.activeAlarmsBanner.classList.remove('hidden');
            dom.alarmBannerTitle.textContent = `🚨 ALERTA CRÍTICO: ${criticalDevices.length} FREEZER(S) FORA DA FAIXA SEGURA!`;
            dom.alarmBannerDesc.textContent = `${first.name} atingiu ${(first.current_temp || 0).toFixed(1)}°C (limite máx: ${first.temp_max}°C).`;
        } else {
            dom.activeAlarmsBanner.classList.add('hidden');
        }
    }

    function renderDevicesGrid() {
        const filter = state.activeFilter;
        let list = state.devices;

        if (filter === 'danger') {
            list = list.filter(d => d.status === 'ALERTA' || d.status === 'CRITICO');
        } else if (filter !== 'all') {
            list = list.filter(d => d.category === filter);
        }

        if (list.length === 0) {
            dom.devicesGrid.innerHTML = `
                <div class="loading-state">
                    <p class="text-muted">Nenhum freezer encontrado para o filtro selecionado.</p>
                </div>
            `;
            return;
        }

        dom.devicesGrid.innerHTML = list.map(device => buildCardHTML(device)).join('');
        attachCardListeners();
    }

    function buildCardHTML(d) {
        const temp = d.current_temp !== null && d.current_temp !== undefined ? d.current_temp.toFixed(1) : '--';
        const hum = d.current_humidity !== null && d.current_humidity !== undefined ? `${d.current_humidity.toFixed(0)}%` : '--%';
        const bat = d.battery_level !== null && d.battery_level !== undefined ? `${d.battery_level}%` : '--%';
        const batClass = (d.battery_level !== null && d.battery_level <= 20) ? 'color: var(--color-crimson-danger); font-weight: bold;' : '';
        const status = d.status || 'NORMAL';

        const range = (d.temp_max - d.temp_min) || 1;
        let percent = 50;
        if (d.current_temp !== null) {
            percent = ((d.current_temp - d.temp_min) / range) * 100;
            percent = Math.max(5, Math.min(95, percent));
        }

        const icons = {
            congelados: '🧊',
            carnes: '🥩',
            resfriados: '🥛',
            vacinas: '💉'
        };
        const catIcon = icons[d.category] || '❄️';
        
        let certBadge = '';
        if (d.calibration_cert) {
            certBadge = `<span style="font-size: 0.8em; background: rgba(56, 189, 248, 0.2); border: 1px solid var(--color-sky-accent); color: var(--color-sky-accent); padding: 2px 6px; border-radius: 4px; margin-left: 8px;" title="Certificado: ${escapeHtml(d.calibration_cert)}">✅ RBC</span>`;
        }

        return `
            <div class="freezer-card status-${status}" id="card-${d.id}" data-id="${d.id}">
                <div class="card-header">
                    <div class="card-title-group">
                        <h3>${catIcon} ${escapeHtml(d.name)} ${certBadge}</h3>
                        <div class="card-location">${escapeHtml(d.location || 'Local não definido')}</div>
                    </div>
                    <span class="status-badge ${status}" id="badge-${d.id}">${status}</span>
                </div>

                <div class="temp-display-area">
                    <span class="temp-huge" id="temp-${d.id}">${temp}</span>
                    <span class="temp-unit">°C</span>
                </div>

                <div class="thermal-gauge-wrap">
                    <div class="gauge-labels">
                        <span>Min: ${d.temp_min}°C</span>
                        <span>Máx: ${d.temp_max}°C</span>
                    </div>
                    <div class="gauge-bar-track">
                        <div class="gauge-pin" id="pin-${d.id}" style="left: ${percent}%"></div>
                    </div>
                </div>

                <div class="card-metrics-row">
                    <div class="metric-item">
                        <span class="metric-label">Umidade</span>
                        <span class="metric-val" id="hum-${d.id}">${hum}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Bateria</span>
                        <span class="metric-val" id="bat-${d.id}" style="${batClass}">🔋 ${bat}</span>
                    </div>
                    <div class="metric-item">
                        <span class="metric-label">Categoria</span>
                        <span class="metric-val">${capitalize(d.category)}</span>
                    </div>
                </div>

                <div class="card-actions">
                    <button class="btn btn-secondary view-chart-btn" data-id="${d.id}">
                        📊 Gráfico
                    </button>
                    <button class="btn btn-outline edit-device-btn" data-id="${d.id}" title="Ajustar limites de temperatura">
                        ⚙️ Limites
                    </button>
                    <button class="btn btn-outline simulate-door-btn" data-id="${d.id}" title="Simula porta aberta / elevação térmica">
                        ⚡ Spike
                    </button>
                </div>
            </div>
        `;
    }

    function updateCardElement(d) {
        const card = document.getElementById(`card-${d.id}`);
        if (!card) return;

        card.className = `freezer-card status-${d.status}`;
        
        const badge = document.getElementById(`badge-${d.id}`);
        if (badge) {
            badge.className = `status-badge ${d.status}`;
            badge.textContent = d.status;
        }

        const tempEl = document.getElementById(`temp-${d.id}`);
        if (tempEl && d.current_temp !== null) {
            tempEl.textContent = d.current_temp.toFixed(1);
        }

        const humEl = document.getElementById(`hum-${d.id}`);
        if (humEl && d.current_humidity !== null) {
            humEl.textContent = `${d.current_humidity.toFixed(0)}%`;
        }

        const batEl = document.getElementById(`bat-${d.id}`);
        if (batEl && d.battery_level !== null) {
            batEl.textContent = `🔋 ${d.battery_level}%`;
            if (d.battery_level <= 20) {
                batEl.style.color = 'var(--color-crimson-danger)';
                batEl.style.fontWeight = 'bold';
            } else {
                batEl.style.color = '';
                batEl.style.fontWeight = '';
            }
        }

        const pinEl = document.getElementById(`pin-${d.id}`);
        if (pinEl && d.current_temp !== null) {
            const range = (d.temp_max - d.temp_min) || 1;
            let percent = ((d.current_temp - d.temp_min) / range) * 100;
            percent = Math.max(5, Math.min(95, percent));
            pinEl.style.left = `${percent}%`;
        }
    }

    function attachCardListeners() {
        document.querySelectorAll('.view-chart-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.dataset.id;
                const dev = state.devices.find(d => d.id === id);
                if (dev) openChartModal(dev);
            });
        });

        document.querySelectorAll('.edit-device-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const id = btn.dataset.id;
                const dev = state.devices.find(d => d.id === id);
                if (dev) openDeviceModal(dev);
            });
        });

        document.querySelectorAll('.simulate-door-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const id = btn.dataset.id;
                btn.disabled = true;
                btn.textContent = 'Simulando...';
                try {
                    await secureFetch('/api/system/simulate-incident', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ device_id: id, anomaly_type: 'DOOR_OPEN' })
                    });
                    setTimeout(async () => {
                        await secureFetch('/api/system/clear-incident', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({ device_id: id })
                        });
                        btn.disabled = false;
                        btn.textContent = '⚡ Spike';
                    }, 8000);
                } catch (e) {
                    btn.disabled = false;
                    btn.textContent = '⚡ Spike';
                }
            });
        });
    }

    function renderAlarmsTable() {
        dom.alarmCountBadge.textContent = `${state.alarms.length} Registros`;
        if (state.alarms.length === 0) {
            dom.alarmsTableBody.innerHTML = `
                <tr>
                    <td colspan="7" class="text-muted text-center">Nenhuma violação registrada até o momento. Todos os freezers operando em conformidade.</td>
                </tr>
            `;
            return;
        }

        dom.alarmsTableBody.innerHTML = state.alarms.slice(0, 15).map(a => {
            const d = new Date(a.triggered_at);
            const timeStr = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
            const sevBadge = a.severity === 'CRITICAL' ? '<span class="status-badge CRITICO">CRÍTICO</span>' : '<span class="status-badge ALERTA">ALERTA</span>';
            const statusBadge = a.status === 'RESOLVED' ? '<span class="badge" style="color: var(--color-emerald-safe)">RESOLVIDO</span>' : (a.status === 'ACKNOWLEDGED' ? '<span class="badge">SILENCIADO</span>' : '<span class="badge" style="color: var(--color-crimson-danger); font-weight: bold;">ATIVO</span>');

            let actionBtn = '';
            if (a.status === 'ACTIVE' || a.status === 'CRITICO' || a.status === 'ALERTA') {
                 // Permitir silenciar alarmes que ainda não estão silenciados nem resolvidos
                 actionBtn = `<button class="btn btn-outline ack-alarm-btn" style="padding: 4px 8px; font-size: 0.8em;" data-device-id="${a.device_id}" data-type="${a.alarm_type}">🔕 Silenciar</button>`;
            }

            return `
                <tr>
                    <td><strong>${timeStr}</strong></td>
                    <td>${escapeHtml(a.device_name || a.device_id)}</td>
                    <td>${sevBadge}</td>
                    <td><strong>${a.value}°C</strong> / ${a.threshold}°C</td>
                    <td>${escapeHtml(a.message)}</td>
                    <td>${statusBadge}</td>
                    <td>${actionBtn}</td>
                </tr>
            `;
        }).join('');

        // Listeners dos botões de silenciar
        document.querySelectorAll('.ack-alarm-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                state.pendingAudit = { device_id: btn.dataset.deviceId, alarm_type: btn.dataset.type };
                dom.auditReason.value = 'Porta aberta acidentalmente';
                dom.auditCustomReason.style.display = 'none';
                dom.auditCustomReason.value = '';
                dom.auditModal.classList.remove('hidden');
            });
        });
    }

    // -------------------------------------------------------------
    // Modais & Configurações do Dashboard
    // -------------------------------------------------------------
    async function openChartModal(device) {
        state.selectedDevice = device;
        dom.modalDeviceTitle.textContent = device.name;
        dom.modalDeviceSubtitle.textContent = `ID: ${device.id} • ${device.location || 'Sem localização'}`;
        dom.modalCurrentTemp.textContent = device.current_temp !== null ? `${device.current_temp.toFixed(1)} °C` : '-- °C';
        dom.modalTempLimits.textContent = `${device.temp_min}°C a ${device.temp_max}°C`;
        dom.modalHumidity.textContent = device.current_humidity ? `${device.current_humidity.toFixed(1)} %` : '-- %';
        dom.modalBattery.textContent = `${device.battery_level || 100}%`;

        dom.chartModal.classList.remove('hidden');

        try {
            const res = await secureFetch(`/api/devices/${device.id}/history?limit=40`);
            const logs = res.ok ? await res.json() : [];
            chartManager.render(logs, device);
        } catch (e) {
            console.error('Erro ao carregar histórico:', e);
        }
    }

    function openDeviceModal(device = null) {
        dom.deviceModal.classList.remove('hidden');
        if (device) {
            dom.deviceModalTitle.textContent = 'Editar Limites do Freezer';
            dom.editDeviceId.value = device.id;
            dom.inputDeviceId.value = device.id;
            dom.inputDeviceId.disabled = true;
            dom.inputDeviceName.value = device.name;
            dom.inputCategory.value = device.category || 'congelados';
            dom.inputLocation.value = device.location || '';
            dom.inputTempMin.value = device.temp_min;
            dom.inputTempMax.value = device.temp_max;
            dom.inputCalibrationCert.value = device.calibration_cert || '';
            dom.inputTempOffset.value = device.temp_offset || '0.0';
            dom.inputLocalIp.value = device.local_ip || '';
            dom.inputLocalKey.value = device.local_key || '';
        } else {
            dom.deviceModalTitle.textContent = 'Cadastrar Sensor / Freezer Tuya';
            dom.editDeviceId.value = '';
            dom.inputDeviceId.value = '';
            dom.inputDeviceId.disabled = false;
            dom.inputDeviceName.value = '';
            dom.inputCategory.value = 'congelados';
            dom.inputLocation.value = '';
            dom.inputTempMin.value = '-22.0';
            dom.inputTempMax.value = '-15.0';
            dom.inputCalibrationCert.value = '';
            dom.inputTempOffset.value = '0.0';
            dom.inputLocalIp.value = '';
            dom.inputLocalKey.value = '';
        }
    }

    dom.deviceForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const editId = dom.editDeviceId.value;
        const payload = {
            id: dom.inputDeviceId.value.trim(),
            name: dom.inputDeviceName.value.trim(),
            category: dom.inputCategory.value,
            location: dom.inputLocation.value.trim(),
            temp_min: parseFloat(dom.inputTempMin.value),
            temp_max: parseFloat(dom.inputTempMax.value),
            calibration_cert: dom.inputCalibrationCert.value.trim() || null,
            temp_offset: parseFloat(dom.inputTempOffset.value) || 0.0,
            local_ip: dom.inputLocalIp.value.trim() || null,
            local_key: dom.inputLocalKey.value.trim() || null
        };

        try {
            if (editId) {
                const res = await secureFetch(`/api/devices/${editId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) throw new Error('Falha ao atualizar limites.');
            } else {
                const res = await secureFetch('/api/devices', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(payload)
                });
                if (!res.ok) {
                    const err = await res.json();
                    alert(`Erro: ${err.detail || 'Não foi possível cadastrar.'}`);
                    return;
                }
            }

            dom.deviceModal.classList.add('hidden');
            await fetchDevices(false);
            await fetchOverview();
        } catch (err) {
            alert(err.message);
        }
    });

    // Listeners do Dashboard
    document.querySelectorAll('.pill').forEach(pill => {
        pill.addEventListener('click', () => {
            document.querySelectorAll('.pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            state.activeFilter = pill.dataset.filter;
            renderDevicesGrid();
        });
    });

    dom.addDeviceBtn.addEventListener('click', () => openDeviceModal());
    dom.systemInfoBtn.addEventListener('click', () => {
        dom.systemModal.classList.remove('hidden');
        fetchOverview();
    });

    dom.testSimulationBtn.addEventListener('click', async () => {
        if (state.devices.length === 0) return;
        const first = state.devices[0];
        dom.testSimulationBtn.disabled = true;
        dom.testSimulationBtn.textContent = '⚡ Disparando...';
        await secureFetch('/api/system/simulate-incident', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device_id: first.id, anomaly_type: 'DOOR_OPEN' })
        });
        setTimeout(async () => {
            await secureFetch('/api/system/clear-incident', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ device_id: first.id })
            });
            dom.testSimulationBtn.disabled = false;
            dom.testSimulationBtn.textContent = '⚡ Testar Alarme';
        }, 7000);
    });

    [dom.closeChartModalBtn, dom.closeChartModalFooterBtn].forEach(b => b.addEventListener('click', () => {
        dom.chartModal.classList.add('hidden');
        state.selectedDevice = null;
    }));

    [dom.closeDeviceModalBtn, dom.cancelDeviceModalBtn].forEach(b => b.addEventListener('click', () => {
        dom.deviceModal.classList.add('hidden');
    }));

    [dom.closeSystemModalBtn, dom.closeSystemModalFooterBtn].forEach(b => b.addEventListener('click', () => {
        dom.systemModal.classList.add('hidden');
    }));

    dom.editLimitsFromChartBtn.addEventListener('click', () => {
        if (state.selectedDevice) {
            dom.chartModal.classList.add('hidden');
            openDeviceModal(state.selectedDevice);
        }
    });

    dom.silenceAlarmBannerBtn.addEventListener('click', () => {
        dom.activeAlarmsBanner.classList.add('hidden');
    });

    dom.soundToggleBtn.addEventListener('click', () => {
        const enabled = socket.toggleSound();
        dom.soundIcon.textContent = enabled ? '🔔' : '🔕';
        dom.soundToggleBtn.title = enabled ? 'Som de alarme ativado' : 'Som de alarme desativado';
    });

    dom.themeToggleBtn.addEventListener('click', () => {
        state.isDarkTheme = !state.isDarkTheme;
        const theme = state.isDarkTheme ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', theme);
        dom.themeIcon.textContent = state.isDarkTheme ? '🌙' : '☀️';
        localStorage.setItem('controlcold_theme', theme);
        if (state.selectedDevice) {
            chartManager.render([], state.selectedDevice);
        }
    });

    dom.sendTelegramTestBtn.addEventListener('click', async () => {
        const btn = dom.sendTelegramTestBtn;
        const resultEl = dom.telegramTestResult;
        btn.disabled = true;
        btn.textContent = 'Enviando...';
        resultEl.textContent = 'Disparando requisição ao bot...';
        resultEl.className = 'text-sm mt-2 text-muted';

        try {
            const res = await secureFetch('/api/system/test-telegram', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ chat_id: dom.testChatId.value.trim() || null })
            });
            const data = await res.json();
            resultEl.textContent = data.message;
            resultEl.className = `text-sm mt-2 ${data.success ? 'status-NORMAL' : 'status-CRITICO'}`;
        } catch (e) {
            resultEl.textContent = 'Erro de comunicação ao enviar teste.';
            resultEl.className = 'text-sm mt-2 status-CRITICO';
        } finally {
            btn.disabled = false;
            btn.textContent = 'Disparar Teste';
        }
    });

    // Auditoria (Silenciamento de Alarmes)
    dom.auditReason.addEventListener('change', (e) => {
        if (e.target.value === 'Outro') {
            dom.auditCustomReason.style.display = 'block';
        } else {
            dom.auditCustomReason.style.display = 'none';
        }
    });

    [dom.closeAuditModalBtn, dom.cancelAuditBtn].forEach(btn => {
        btn.addEventListener('click', () => dom.auditModal.classList.add('hidden'));
    });

    dom.confirmAuditBtn.addEventListener('click', async () => {
        const reasonSelect = dom.auditReason.value;
        const reason = reasonSelect === 'Outro' ? dom.auditCustomReason.value.trim() : reasonSelect;

        if (!reason) {
            alert('Por favor, informe o motivo do silenciamento.');
            return;
        }

        if (!state.pendingAudit) return;

        try {
            dom.confirmAuditBtn.disabled = true;
            dom.confirmAuditBtn.textContent = 'Registrando...';

            const payload = {
                device_id: state.pendingAudit.device_id,
                action_type: "ALARM_ACKNOWLEDGED",
                reason: reason,
                details: { alarm_type: state.pendingAudit.alarm_type }
            };

            const res = await secureFetch('/api/audit/log', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (res.ok) {
                // Atualiza localmente
                const matching = state.alarms.find(a => a.device_id === state.pendingAudit.device_id && a.alarm_type === state.pendingAudit.alarm_type);
                if (matching) {
                    matching.status = 'ACKNOWLEDGED';
                    renderAlarmsTable();
                    updateActiveAlarmsBanner();
                }
                dom.auditModal.classList.add('hidden');
            } else {
                alert('Erro ao registrar auditoria.');
            }
        } catch (e) {
            alert('Falha de conexão.');
        } finally {
            dom.confirmAuditBtn.disabled = false;
            dom.confirmAuditBtn.textContent = 'Confirmar e Silenciar';
        }
    });

    // Geração de Relatório PDF
    dom.reportBtn.addEventListener('click', () => {
        if (!state.authToken) return;
        // Chama a rota de PDF (abrindo direto para download usando o token, mas como é GET, 
        // precisamos lidar com auth. Já que o browser direto não envia header Bearer no open,
        // faremos o fetch com blob).
        dom.reportBtn.disabled = true;
        dom.reportBtn.innerHTML = '⏳ Gerando...';

        secureFetch('/api/reports/pdf')
            .then(res => {
                if (!res.ok) throw new Error('Falha ao gerar relatório');
                return res.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                // nome padrão
                a.download = `Relatorio_ControlCold_${new Date().toISOString().slice(0,10)}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
            })
            .catch(e => alert(e.message))
            .finally(() => {
                dom.reportBtn.disabled = false;
                dom.reportBtn.innerHTML = '🖨️ <span class="desktop-only">Relatório PDF</span>';
            });
    });


    // Ponto de Partida: Validação da Sessão
    initSession();

    // -------------------------------------------------------------
    // Push Notifications (PWA Native)
    // -------------------------------------------------------------
    function urlBase64ToUint8Array(base64String) {
        const padding = '='.repeat((4 - base64String.length % 4) % 4);
        const base64 = (base64String + padding)
            .replace(/\-/g, '+')
            .replace(/_/g, '/');
        const rawData = window.atob(base64);
        const outputArray = new Uint8Array(rawData.length);
        for (let i = 0; i < rawData.length; ++i) {
            outputArray[i] = rawData.charCodeAt(i);
        }
        return outputArray;
    }

    async function initPushNotifications() {
        if (!('serviceWorker' in navigator) || !('PushManager' in window)) return;
        
        try {
            const swReg = await navigator.serviceWorker.ready;
            
            // Pede permissão
            const permission = await Notification.requestPermission();
            if (permission !== 'granted') return;

            // Pega VAPID Key
            const vapidRes = await secureFetch('/api/push/vapid-public-key');
            if (!vapidRes.ok) return;
            const { public_key } = await vapidRes.json();
            
            const convertedVapidKey = urlBase64ToUint8Array(public_key);
            
            let subscription = await swReg.pushManager.getSubscription();
            if (!subscription) {
                subscription = await swReg.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: convertedVapidKey
                });
            }

            // Envia para o backend
            await secureFetch('/api/push/subscribe', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(subscription)
            });

        } catch (e) {
            console.error('Erro ao inicializar Push Notifications:', e);
        }
    }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str)
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function capitalize(str) {
        if (!str) return '';
        return str.charAt(0).toUpperCase() + str.slice(1);
    }
});
