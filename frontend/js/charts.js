/**
 * AntiGravity ColdChain - Gerenciador de Gráficos de Telemetria
 */

class TelemetryChartManager {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.chart = null;
        this.currentDeviceId = null;
        this.tempMin = -22;
        this.tempMax = -15;
    }

    render(logs, device) {
        if (!this.canvas) return;
        this.currentDeviceId = device.id;
        this.tempMin = device.temp_min;
        this.tempMax = device.temp_max;

        const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
        const gridColor = isDark ? 'rgba(255, 255, 255, 0.07)' : 'rgba(0, 0, 0, 0.07)';
        const textColor = isDark ? '#94a3b8' : '#475569';

        const labels = logs.map(item => {
            const d = new Date(item.timestamp);
            return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
        });

        const temps = logs.map(item => item.temperature);
        const hums = logs.map(item => item.humidity);

        if (this.chart) {
            this.chart.destroy();
        }

        // Verifica se Chart.js está disponível
        if (typeof Chart === 'undefined') {
            console.warn('Chart.js ainda não carregado.');
            return;
        }

        const ctx = this.canvas.getContext('2d');

        // Gradiente sob a linha de temperatura
        const tempGradient = ctx.createLinearGradient(0, 0, 0, 300);
        tempGradient.addColorStop(0, 'rgba(56, 189, 248, 0.35)');
        tempGradient.addColorStop(1, 'rgba(56, 189, 248, 0.0)');

        this.chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Temperatura (°C)',
                        data: temps,
                        borderColor: '#38bdf8',
                        backgroundColor: tempGradient,
                        borderWidth: 2.5,
                        fill: true,
                        tension: 0.35,
                        pointRadius: 2.5,
                        pointHoverRadius: 6,
                        pointBackgroundColor: '#38bdf8',
                        yAxisID: 'y'
                    },
                    {
                        label: 'Umidade (%)',
                        data: hums,
                        borderColor: '#10b981',
                        borderWidth: 1.5,
                        borderDash: [4, 4],
                        fill: false,
                        tension: 0.3,
                        pointRadius: 0,
                        pointHoverRadius: 4,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: {
                    mode: 'index',
                    intersect: false
                },
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: textColor,
                            font: { family: 'Inter', size: 12, weight: '500' }
                        }
                    },
                    tooltip: {
                        backgroundColor: isDark ? '#1e293b' : '#ffffff',
                        titleColor: isDark ? '#f8fafc' : '#0f172a',
                        bodyColor: isDark ? '#94a3b8' : '#334155',
                        borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.1)',
                        borderWidth: 1,
                        padding: 10,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                if (context.parsed.y !== null) {
                                    label += context.parsed.y + (context.datasetIndex === 0 ? ' °C' : ' %');
                                }
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: gridColor },
                        ticks: { color: textColor, maxRotation: 0, autoSkip: true, maxTicksLimit: 8 }
                    },
                    y: {
                        type: 'linear',
                        display: true,
                        position: 'left',
                        grid: { color: gridColor },
                        ticks: {
                            color: textColor,
                            callback: (value) => value + '°C'
                        }
                    },
                    y1: {
                        type: 'linear',
                        display: true,
                        position: 'right',
                        min: 0,
                        max: 100,
                        grid: { drawOnChartArea: false },
                        ticks: {
                            color: textColor,
                            callback: (value) => value + '%'
                        }
                    }
                }
            }
        });
    }

    appendReading(reading) {
        if (!this.chart || reading.device_id !== this.currentDeviceId) return;

        const d = new Date(reading.timestamp || Date.now());
        const label = d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });

        this.chart.data.labels.push(label);
        this.chart.data.datasets[0].data.push(reading.temperature);
        if (this.chart.data.datasets[1]) {
            this.chart.data.datasets[1].data.push(reading.humidity);
        }

        // Mantém janela deslizante de 60 pontos
        if (this.chart.data.labels.length > 60) {
            this.chart.data.labels.shift();
            this.chart.data.datasets[0].data.shift();
            if (this.chart.data.datasets[1]) {
                this.chart.data.datasets[1].data.shift();
            }
        }

        this.chart.update('none');
    }
}

window.TelemetryChartManager = TelemetryChartManager;
