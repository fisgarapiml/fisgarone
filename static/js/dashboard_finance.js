// Dashboard Financeiro - JavaScript
class FinancialDashboard {
    constructor() {
        this.charts = {};
        this.data = {};
        this.currentFilter = 'all';
        this.init();
    }

    async init() {
        this.showLoading();
        await this.loadData();
        this.initializeCharts();
        this.setupEventListeners();
        this.hideLoading();
    }

    showLoading() {
        document.getElementById('loadingOverlay').classList.add('active');
    }

    hideLoading() {
        document.getElementById('loadingOverlay').classList.remove('active');
    }

    async loadData() {
        try {
            const response = await fetch('/financeiro/dashboard_finance/api/dados-completos');
            if (!response.ok) throw new Error('Erro ao carregar dados');
            this.data = await response.json();
            this.updateSummaryCards();
            this.updateTransactions();
        } catch (error) {
            console.error('Erro ao carregar dados:', error);
            this.showError('Erro ao carregar dados do dashboard');
        }
    }

    updateSummaryCards() {
        const { resumo } = this.data;
        
        // Atualizar valores dos cards
        this.updateCardValue('totalEntradas', resumo.total_entradas);
        this.updateCardValue('totalSaidas', resumo.total_saidas);
        this.updateCardValue('saldoAtual', resumo.saldo_atual);
        this.updateCardValue('contasVencidas', resumo.contas_vencidas);
        this.updateCardValue('contasHoje', resumo.contas_hoje);
        this.updateCardValue('entradasPendentes', resumo.entradas_pendentes);

        // Atualizar trend do saldo
        const saldoTrend = document.getElementById('trendSaldo');
        if (resumo.saldo_atual > 0) {
            saldoTrend.className = 'card-trend positive';
            saldoTrend.innerHTML = '<i class="ri-arrow-up-line"></i><span>Positivo</span>';
        } else if (resumo.saldo_atual < 0) {
            saldoTrend.className = 'card-trend negative';
            saldoTrend.innerHTML = '<i class="ri-arrow-down-line"></i><span>Negativo</span>';
        } else {
            saldoTrend.className = 'card-trend';
            saldoTrend.innerHTML = '<i class="ri-subtract-line"></i><span>Neutro</span>';
        }
    }

    updateCardValue(elementId, value) {
        const element = document.getElementById(elementId);
        if (element) {
            element.textContent = this.formatCurrency(value);
        }
    }

    formatCurrency(value) {
        return new Intl.NumberFormat('pt-BR', {
            style: 'currency',
            currency: 'BRL'
        }).format(Math.abs(value));
    }

    initializeCharts() {
        this.createFluxoCaixaChart();
        this.createCategoriasChart();
        this.createCanaisChart();
        this.createEvolucaoChart();
    }

    createFluxoCaixaChart() {
        const ctx = document.getElementById('fluxoCaixaChart').getContext('2d');
        const { fluxo_caixa } = this.data;

        if (!fluxo_caixa || fluxo_caixa.length === 0) {
            console.warn('Dados de fluxo de caixa não disponíveis');
            return;
        }

        const labels = fluxo_caixa.map(item => item.mes);
        const entradas = fluxo_caixa.map(item => item.entradas);
        const saidas = fluxo_caixa.map(item => Math.abs(item.saidas));
        const saldos = fluxo_caixa.map(item => item.saldo);

        this.charts.fluxoCaixa = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Entradas',
                        data: entradas,
                        borderColor: '#00FF88',
                        backgroundColor: 'rgba(0, 255, 136, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Saídas',
                        data: saidas,
                        borderColor: '#FF4757',
                        backgroundColor: 'rgba(255, 71, 87, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4
                    },
                    {
                        label: 'Saldo',
                        data: saldos,
                        borderColor: '#00BFFF',
                        backgroundColor: 'rgba(0, 191, 255, 0.1)',
                        borderWidth: 3,
                        fill: false,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                        labels: {
                            color: '#1A1F2E',
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#1A1F2E',
                        bodyColor: '#4A5568',
                        borderColor: '#00BFFF',
                        borderWidth: 1,
                        callbacks: {
                            label: (context) => {
                                return `${context.dataset.label}: ${this.formatCurrency(context.parsed.y)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(226, 232, 240, 0.5)'
                        },
                        ticks: {
                            color: '#4A5568'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(226, 232, 240, 0.5)'
                        },
                        ticks: {
                            color: '#4A5568',
                            callback: (value) => this.formatCurrency(value)
                        }
                    }
                }
            }
        });
    }

    createCategoriasChart() {
        const ctx = document.getElementById('categoriasChart').getContext('2d');
        const { categorias_despesas } = this.data;

        if (!categorias_despesas || categorias_despesas.length === 0) {
            console.warn('Dados de categorias de despesas não disponíveis');
            return;
        }

        const labels = categorias_despesas.map(item => item.categoria);
        const values = categorias_despesas.map(item => item.valor);
        const colors = this.generateColors(labels.length);

        this.charts.categorias = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderColor: colors.map(color => color.replace('0.8', '1')),
                    borderWidth: 2,
                    hoverBorderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#1A1F2E',
                            usePointStyle: true,
                            padding: 15,
                            generateLabels: (chart) => {
                                const data = chart.data;
                                return data.labels.map((label, i) => ({
                                    text: `${label}: ${this.formatCurrency(data.datasets[0].data[i])}`,
                                    fillStyle: data.datasets[0].backgroundColor[i],
                                    strokeStyle: data.datasets[0].borderColor[i],
                                    pointStyle: 'circle'
                                }));
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#1A1F2E',
                        bodyColor: '#4A5568',
                        borderColor: '#00BFFF',
                        borderWidth: 1,
                        callbacks: {
                            label: (context) => {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return `${context.label}: ${this.formatCurrency(context.parsed)} (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '60%'
            }
        });
    }

    createCanaisChart() {
        const ctx = document.getElementById('canaisChart').getContext('2d');
        const { canais_receita } = this.data;

        if (!canais_receita || canais_receita.length === 0) {
            console.warn('Dados de canais de receita não disponíveis');
            return;
        }

        const labels = canais_receita.map(item => item.canal);
        const values = canais_receita.map(item => item.valor);
        const colors = this.generateColors(labels.length, 'success');

        this.charts.canais = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderColor: colors.map(color => color.replace('0.8', '1')),
                    borderWidth: 2,
                    hoverBorderWidth: 3
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: {
                            color: '#1A1F2E',
                            usePointStyle: true,
                            padding: 15,
                            generateLabels: (chart) => {
                                const data = chart.data;
                                return data.labels.map((label, i) => ({
                                    text: `${label}: ${this.formatCurrency(data.datasets[0].data[i])}`,
                                    fillStyle: data.datasets[0].backgroundColor[i],
                                    strokeStyle: data.datasets[0].borderColor[i],
                                    pointStyle: 'circle'
                                }));
                            }
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#1A1F2E',
                        bodyColor: '#4A5568',
                        borderColor: '#00BFFF',
                        borderWidth: 1,
                        callbacks: {
                            label: (context) => {
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((context.parsed / total) * 100).toFixed(1);
                                return `${context.label}: ${this.formatCurrency(context.parsed)} (${percentage}%)`;
                            }
                        }
                    }
                },
                cutout: '60%'
            }
        });
    }

    createEvolucaoChart() {
        const ctx = document.getElementById('evolucaoChart').getContext('2d');
        const { fluxo_caixa } = this.data;

        if (!fluxo_caixa || fluxo_caixa.length === 0) {
            console.warn('Dados de evolução não disponíveis');
            return;
        }

        const labels = fluxo_caixa.map(item => item.mes);
        const entradas = fluxo_caixa.map(item => item.entradas);
        const saidas = fluxo_caixa.map(item => Math.abs(item.saidas));

        this.charts.evolucao = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [
                    {
                        label: 'Entradas',
                        data: entradas,
                        borderColor: '#00FF88',
                        backgroundColor: 'rgba(0, 255, 136, 0.2)',
                        borderWidth: 3,
                        fill: '+1',
                        tension: 0.4
                    },
                    {
                        label: 'Saídas',
                        data: saidas,
                        borderColor: '#FF4757',
                        backgroundColor: 'rgba(255, 71, 87, 0.2)',
                        borderWidth: 3,
                        fill: 'origin',
                        tension: 0.4
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
                            color: '#1A1F2E',
                            usePointStyle: true,
                            padding: 20
                        }
                    },
                    tooltip: {
                        backgroundColor: 'rgba(255, 255, 255, 0.95)',
                        titleColor: '#1A1F2E',
                        bodyColor: '#4A5568',
                        borderColor: '#00BFFF',
                        borderWidth: 1,
                        callbacks: {
                            label: (context) => {
                                return `${context.dataset.label}: ${this.formatCurrency(context.parsed.y)}`;
                            },
                            afterBody: (tooltipItems) => {
                                const entradas = tooltipItems.find(item => item.datasetIndex === 0)?.parsed.y || 0;
                                const saidas = tooltipItems.find(item => item.datasetIndex === 1)?.parsed.y || 0;
                                const saldo = entradas - saidas;
                                return `Saldo: ${this.formatCurrency(saldo)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            color: 'rgba(226, 232, 240, 0.5)'
                        },
                        ticks: {
                            color: '#4A5568'
                        }
                    },
                    y: {
                        grid: {
                            color: 'rgba(226, 232, 240, 0.5)'
                        },
                        ticks: {
                            color: '#4A5568',
                            callback: (value) => this.formatCurrency(value)
                        }
                    }
                }
            }
        });
    }

    generateColors(count, type = 'primary') {
        const baseColors = {
            primary: ['#00BFFF', '#0099CC', '#87CEEB', '#4169E1', '#1E90FF'],
            success: ['#00FF88', '#00CC6A', '#32CD32', '#00FA9A', '#98FB98'],
            mixed: ['#00BFFF', '#00FF88', '#FFD700', '#FF4757', '#74B9FF', '#A29BFE', '#FD79A8', '#FDCB6E']
        };

        const colors = baseColors[type] || baseColors.mixed;
        const result = [];

        for (let i = 0; i < count; i++) {
            const baseColor = colors[i % colors.length];
            const opacity = 0.8 - (Math.floor(i / colors.length) * 0.1);
            result.push(baseColor.replace(')', `, ${opacity})`).replace('rgb', 'rgba').replace('#', 'rgba(') + ')');
        }

        return result;
    }

    updateTransactions() {
        const { transacoes } = this.data;
        const container = document.getElementById('transactionsList');
        
        if (!transacoes || transacoes.length === 0) {
            container.innerHTML = '<div class="no-transactions">Nenhuma transação encontrada</div>';
            return;
        }

        const filteredTransactions = this.currentFilter === 'all' 
            ? transacoes 
            : transacoes.filter(t => t.tipo === this.currentFilter);

        container.innerHTML = filteredTransactions.map(transaction => `
            <div class="transaction-item">
                <div class="transaction-icon ${transaction.tipo}">
                    <i class="ri-${transaction.tipo === 'entrada' ? 'arrow-down' : 'arrow-up'}-line"></i>
                </div>
                <div class="transaction-details">
                    <div class="transaction-description">${transaction.descricao}</div>
                    <div class="transaction-meta">${transaction.data} • ${transaction.detalhes}</div>
                </div>
                <div class="transaction-value ${transaction.tipo}">
                    ${transaction.tipo === 'entrada' ? '+' : '-'}${this.formatCurrency(transaction.valor)}
                </div>
            </div>
        `).join('');
    }

    setupEventListeners() {
        // Chart type toggles
        document.querySelectorAll('.chart-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const chartName = e.target.dataset.chart;
                const chartType = e.target.dataset.type;
                this.changeChartType(chartName, chartType, e.target);
            });
        });

        // Transaction filters
        document.querySelectorAll('.btn-filter').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.btn-filter').forEach(b => b.classList.remove('active'));
                e.target.classList.add('active');
            });
        });
    }

    changeChartType(chartName, newType, button) {
        // Update active button
        button.parentElement.querySelectorAll('.chart-btn').forEach(btn => btn.classList.remove('active'));
        button.classList.add('active');

        // Destroy and recreate chart with new type
        const chartMap = {
            'fluxo': 'fluxoCaixa',
            'despesas': 'categorias',
            'receitas': 'canais',
            'evolucao': 'evolucao'
        };

        const chartKey = chartMap[chartName];
        if (this.charts[chartKey]) {
            const chartData = this.charts[chartKey].data;
            const chartOptions = this.charts[chartKey].options;
            
            this.charts[chartKey].destroy();
            
            // Update chart type
            chartOptions.plugins = chartOptions.plugins || {};
            
            const ctx = document.getElementById(`${chartKey}Chart`).getContext('2d');
            this.charts[chartKey] = new Chart(ctx, {
                type: newType,
                data: chartData,
                options: chartOptions
            });
        }
    }

    showError(message) {
        // Simple error display - could be enhanced with a proper notification system
        console.error(message);
        alert(message);
    }

    async refreshDashboard() {
        this.showLoading();
        await this.loadData();
        
        // Destroy existing charts
        Object.values(this.charts).forEach(chart => chart.destroy());
        this.charts = {};
        
        // Recreate charts
        this.initializeCharts();
        this.hideLoading();
    }
}

// Global functions
function refreshDashboard() {
    if (window.dashboard) {
        window.dashboard.refreshDashboard();
    }
}

function changePeriod() {
    const period = document.getElementById('periodSelect').value;
    console.log('Período alterado para:', period);
    // Implementar lógica de mudança de período
}

function filterTransactions(type) {
    if (window.dashboard) {
        window.dashboard.currentFilter = type;
        window.dashboard.updateTransactions();
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.dashboard = new FinancialDashboard();
});

// Chart.js global configuration
Chart.defaults.font.family = 'Inter, sans-serif';
Chart.defaults.color = '#4A5568';
Chart.defaults.borderColor = 'rgba(226, 232, 240, 0.5)';
Chart.defaults.backgroundColor = 'rgba(0, 191, 255, 0.1)';

