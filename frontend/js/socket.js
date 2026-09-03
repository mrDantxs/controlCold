/**
 * ControlCold - WebSocket & Real-Time Audio Manager
 */

class RealtimeSocket {
    constructor(callbacks = {}) {
        this.callbacks = callbacks;
        this.ws = null;
        this.reconnectAttempts = 0;
        this.maxReconnectDelay = 10000;
        this.soundEnabled = true;
        this.audioCtx = null;
        this.isFallbackPolling = false;
        this.pollInterval = null;
        this.reconnectTimeout = null;
        this.isActive = false;
    }

    start() {
        this.isActive = true;
        this.connectWebSocket();
        this.initAudioContext();
    }

    stop() {
        this.isActive = false;
        if (this.reconnectTimeout) {
            clearTimeout(this.reconnectTimeout);
            this.reconnectTimeout = null;
        }
        this.stopFallbackPolling();
        if (this.ws) {
            try {
                this.ws.close();
            } catch (e) {}
            this.ws = null;
        }
    }

    initAudioContext() {
        const unlockAudio = () => {
            if (!this.audioCtx) {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) {
                    this.audioCtx = new AudioContext();
                }
            } else if (this.audioCtx.state === 'suspended') {
                this.audioCtx.resume();
            }
            window.removeEventListener('click', unlockAudio);
            window.removeEventListener('touchstart', unlockAudio);
        };

        window.addEventListener('click', unlockAudio);
        window.addEventListener('touchstart', unlockAudio);
    }

    playAlarmSound() {
        if (!this.soundEnabled) return;
        try {
            if (!this.audioCtx) {
                const AudioContext = window.AudioContext || window.webkitAudioContext;
                if (AudioContext) this.audioCtx = new AudioContext();
            }
            if (this.audioCtx && this.audioCtx.state === 'suspended') {
                this.audioCtx.resume();
            }

            if (!this.audioCtx) return;

            const now = this.audioCtx.currentTime;
            const osc = this.audioCtx.createOscillator();
            const gain = this.audioCtx.createGain();
            osc.type = 'sawtooth';
            osc.frequency.setValueAtTime(880, now);
            osc.frequency.exponentialRampToValueAtTime(440, now + 0.35);

            gain.gain.setValueAtTime(0.3, now);
            gain.gain.exponentialRampToValueAtTime(0.01, now + 0.35);

            osc.connect(gain);
            gain.connect(this.audioCtx.destination);
            osc.start(now);
            osc.stop(now + 0.36);

            setTimeout(() => {
                if (!this.audioCtx) return;
                const now2 = this.audioCtx.currentTime;
                const osc2 = this.audioCtx.createOscillator();
                const gain2 = this.audioCtx.createGain();
                osc2.type = 'sawtooth';
                osc2.frequency.setValueAtTime(960, now2);
                osc2.frequency.exponentialRampToValueAtTime(480, now2 + 0.35);

                gain2.gain.setValueAtTime(0.35, now2);
                gain2.gain.exponentialRampToValueAtTime(0.01, now2 + 0.35);

                osc2.connect(gain2);
                gain2.connect(this.audioCtx.destination);
                osc2.start(now2);
                osc2.stop(now2 + 0.36);
            }, 250);

        } catch (e) {
            console.warn('Alerta sonoro:', e);
        }
    }

    toggleSound() {
        this.soundEnabled = !this.soundEnabled;
        return this.soundEnabled;
    }

    connectWebSocket() {
        if (!this.isActive) return;

        const token = localStorage.getItem('controlcold_token');
        if (!token) return; // Prevent connecting without token

        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.host;
        const wsUrl = `${protocol}//${host}/ws/live?token=${encodeURIComponent(token)}`;

        try {
            this.ws = new WebSocket(wsUrl);

            this.ws.onopen = () => {
                console.log('⚡ Conexão WebSocket estabelecida.');
                this.reconnectAttempts = 0;
                this.stopFallbackPolling();
                if (this.callbacks.onConnectionChange) {
                    this.callbacks.onConnectionChange(true);
                }
            };

            this.ws.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    const { type, data } = message;

                    if (type === 'TELEMETRY_UPDATE' && this.callbacks.onTelemetryUpdate) {
                        this.callbacks.onTelemetryUpdate(data);
                    } else if (type === 'NEW_ALARM' && this.callbacks.onNewAlarm) {
                        this.playAlarmSound();
                        this.callbacks.onNewAlarm(data);
                    } else if (type === 'ALARM_RESOLVED' && this.callbacks.onAlarmResolved) {
                        this.callbacks.onAlarmResolved(data);
                    }
                } catch (err) {
                    console.error('Erro ao interpretar mensagem WebSocket:', err);
                }
            };

            this.ws.onerror = () => {};

            this.ws.onclose = () => {
                if (!this.isActive) return;
                if (this.callbacks.onConnectionChange) {
                    this.callbacks.onConnectionChange(false);
                }
                this.startFallbackPolling();
                this.scheduleReconnect();
            };

        } catch (err) {
            if (!this.isActive) return;
            this.startFallbackPolling();
            this.scheduleReconnect();
        }
    }

    scheduleReconnect() {
        if (!this.isActive) return;
        this.reconnectAttempts++;
        const delay = Math.min(1500 * Math.pow(1.5, this.reconnectAttempts), this.maxReconnectDelay);
        this.reconnectTimeout = setTimeout(() => {
            if (this.isActive) this.connectWebSocket();
        }, delay);
    }

    startFallbackPolling() {
        if (!this.isActive || this.isFallbackPolling) return;
        this.isFallbackPolling = true;
        this.pollInterval = setInterval(async () => {
            if (this.isActive && this.callbacks.onPollingTick) {
                this.callbacks.onPollingTick();
            }
        }, 4000);
    }

    stopFallbackPolling() {
        if (!this.isFallbackPolling) return;
        this.isFallbackPolling = false;
        if (this.pollInterval) {
            clearInterval(this.pollInterval);
            this.pollInterval = null;
        }
    }
}

window.RealtimeSocket = RealtimeSocket;
