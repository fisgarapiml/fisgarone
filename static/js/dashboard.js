// raiz/static/js/dashboard.js

document.addEventListener('DOMContentLoaded', () => {
    // Referências aos elementos HTML
    const periodSelect = document.getElementById('period-select');
    const startDateInput = document.getElementById('start-date');
    const endDateInput = document.getElementById('end-date');
    const refreshButton = document.getElementById('refresh-data-btn');
    const themeToggleButton = document.getElementById('theme-toggle-btn');
    const loadingOverlay = document.getElementById('loading-overlay');
    const messageBox = document.getElementById('message-box');
    const messageText = document.getElementById('message-text');
    const lightIcon = themeToggleButton.querySelector('.light-icon');
    const darkIcon = themeToggleButton.querySelector('.dark-icon');

    // Elementos de KPI
    const totalSalesValue = document.querySelector('#kpi-total-sales .kpi-value');
    const totalSalesPercent = document.querySelector('#kpi-total-sales .comparison-percent');
    const numOrdersValue = document.querySelector('#kpi-num-orders .kpi-value');
    const numOrdersPercent = document.querySelector('#kpi-num-orders .comparison-percent');
    const averageTicketValue = document.querySelector('#kpi-average-ticket .kpi-value');
    const netRevenueValue = document.querySelector('#kpi-net-revenue .kpi-value'); // Agora para Lucro Real

    // Sparklines (Canvas)
    const sparklineSalesCtx = document.getElementById('sparkline-sales').getContext('2d');
    const sparklineOrdersCtx = document.getElementById('sparkline-orders').getContext('2d');

    // Contextos dos Gráficos principais
    const salesOverTimeCtx = document.getElementById('sales-over-time-chart').getContext('2d');
    const topProductsCtx = document.getElementById('top-products-chart').getContext('2d');
    const topCategoriesCtx = document.getElementById('top-categories-chart').getContext('2d');
    const paymentMethodsCtx = document.getElementById('payment-methods-chart').getContext('2d'); // Agora para Tipo de Conta
    const salesStatusCtx = document.getElementById('sales-status-chart').getContext('2d'); // Agora para Status de Pedido
    const salesByRegionCtx = document.getElementById('sales-by-region-chart').getContext('2d'); // Agora para Transportadora

    // Tabela de Vendas Recentes
    const recentSalesTbody = document.getElementById('recent-sales-tbody');

    // Instâncias de Chart.js (para que possamos destruí-las e recriá-las)
    let salesOverTimeChart, topProductsChart, topCategoriesChart,
        paymentMethodsChart, salesStatusChart, salesByRegionChart;

    // --- Funções Auxiliares ---

    /**
     * Exibe ou oculta o overlay de carregamento.
     * @param {boolean} show - True para exibir, False para ocultar.
     */
    function showLoadingOverlay(show) {
        loadingOverlay.style.opacity = show ? '1' : '0';
        loadingOverlay.style.pointerEvents = show ? 'auto' : 'none';
        // Adiciona/remove placeholders enquanto carrega
        document.querySelectorAll('.data-placeholder').forEach(el => {
            el.classList.toggle('active', show);
        });
        document.querySelectorAll('.data-placeholder-row').forEach(el => {
            el.style.display = show ? 'table-row' : 'none';
        });
        if (show) {
            recentSalesTbody.innerHTML = '<tr><td colspan="5" class="data-placeholder-row">Carregando últimas vendas...</td></tr>';
        }
    }

    /**
     * Exibe uma mensagem na caixa de mensagem customizada.
     * @param {string} message - A mensagem a ser exibida.
     * @param {string} type - Tipo da mensagem (ex: 'error', 'success').
     */
    function showMessage(message, type = 'info') {
        messageText.textContent = message;
        messageBox.style.display = 'flex';
        // Remover classes de tipo anteriores
        messageBox.classList.remove('error', 'success', 'info');
        // Adicionar a nova classe de tipo
        messageBox.classList.add(type);
        setTimeout(() => {
            messageBox.style.display = 'none';
        }, 5000); // Esconde a mensagem após 5 segundos
    }

    /**
     * Formata um valor numérico para moeda BRL.
     * @param {number} value - O valor a ser formatado.
     * @returns {string} O valor formatado como moeda.
     */
    function formatCurrency(value) {
        return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(value);
    }

    /**
     * Formata um valor numérico para porcentagem.
     * @param {number} value - O valor a ser formatado.
     * @returns {string} O valor formatado como porcentagem.
     */
    function formatPercentage(value) {
        return new Intl.NumberFormat('pt-BR', { style: 'percent', minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(value / 100);
    }

    /**
     * Destroi uma instância de Chart.js se ela existir.
     * @param {object} chartInstance - A instância do Chart.js.
     */
    function destroyChart(chartInstance) {
        if (chartInstance) {
            chartInstance.destroy();
        }
    }

    /**
     * Obtém os parâmetros de data e período dos seletores.
     * @returns {object} Um objeto com period, start_date e end_date.
     */
    function getPeriodParams() {
        const period = periodSelect.value;
        let params = { period: period };

        if (period === 'custom') {
            params.start_date = startDateInput.value;
            params.end_date = endDateInput.value;
        }
        return params;
    }

    // --- Função Principal de Busca de Dados ---

    /**
     * Busca todos os dados do dashboard do backend Flask e atualiza a interface.
     */
    async function fetchDashboardData() {
        showLoadingOverlay(true); // Exibe o overlay de carregamento
        const params = getPeriodParams();
        const queryString = new URLSearchParams(params).toString();

        try {
            // Requisições assíncronas para todos os endpoints
            // As URLs agora incluem o prefixo do Blueprint '/shopee/dashboard'
            const [
                summaryRes,
                productsRes,
                categoriesRes,
                salesTimeRes,
                paymentMethodsRes,
                salesStatusRes,
                regionRes,
                recentSalesRes
            ] = await Promise.all([
                fetch(`/shopee/dashboard/api/sales/summary?${queryString}`),
                fetch(`/shopee/dashboard/api/sales/products?${queryString}&limit=7`), // Limita produtos para gráficos
                fetch(`/shopee/dashboard/api/sales/categories?${queryString}&limit=7`), // Limita categorias para gráficos
                fetch(`/shopee/dashboard/api/sales/time?${queryString}&granularity=daily`), // Granularidade diária para sparklines e linha principal
                fetch(`/shopee/dashboard/api/sales/payment_methods?${queryString}`),
                fetch(`/shopee/dashboard/api/sales/status?${queryString}`),
                fetch(`/shopee/dashboard/api/sales/region?${queryString}`),
                fetch(`/shopee/dashboard/api/sales/recent?limit=15`) // Limita últimas vendas para tabela
            ]);

            // Verifica se todas as respostas foram bem-sucedidas
            if (!summaryRes.ok || !productsRes.ok || !categoriesRes.ok || !salesTimeRes.ok ||
                !paymentMethodsRes.ok || !salesStatusRes.ok || !regionRes.ok || !recentSalesRes.ok) {
                // Tenta ler a resposta de erro do servidor
                const errorBody = await (summaryRes.json().catch(() => summaryRes.text()));
                throw new Error(`Erro ao buscar dados: ${summaryRes.status} - ${errorBody.error || errorBody}`);
            }

            const summaryData = await summaryRes.json();
            const productsData = await productsRes.json();
            const categoriesData = await categoriesRes.json();
            const salesTimeData = await salesTimeRes.json();
            const paymentMethodsData = await paymentMethodsRes.json();
            const salesStatusData = await salesStatusRes.json();
            const regionData = await regionRes.json();
            const recentSalesData = await recentSalesRes.json();

            // Atualiza a UI com os dados
            updateKPIs(summaryData, salesTimeData);
            renderCharts(productsData, categoriesData, salesTimeData, paymentMethodsData, salesStatusData, regionData);
            updateRecentSalesTable(recentSalesData);

        } catch (error) {
            console.error('Erro ao buscar dados do dashboard:', error);
            showMessage(`Erro: ${error.message || 'Não foi possível carregar os dados do dashboard. Verifique o servidor e tente novamente.'}`, 'error');
        } finally {
            showLoadingOverlay(false); // Oculta o overlay de carregamento
        }
    }

    // --- Atualização de KPIs e Sparklines ---

    /**
     * Atualiza os valores e comparativos dos KPIs na interface.
     * @param {object} summary - Dados de resumo dos KPIs.
     * @param {Array<object>} salesTimeData - Dados de vendas ao longo do tempo para sparklines.
     */
    function updateKPIs(summary, salesTimeData) {
        totalSalesValue.textContent = formatCurrency(summary.total_sales);
        numOrdersValue.textContent = summary.num_orders.toLocaleString('pt-BR');
        averageTicketValue.textContent = formatCurrency(summary.average_ticket);
        netRevenueValue.textContent = formatCurrency(summary.net_revenue); // Agora é 'lucro_real'

        // Atualiza comparativos percentuais
        totalSalesPercent.textContent = formatPercentage(summary.comparative_data.sales_change_percent);
        totalSalesPercent.classList.toggle('negative', summary.comparative_data.sales_change_percent < 0);
        numOrdersPercent.textContent = formatPercentage(summary.comparative_data.orders_change_percent);
        numOrdersPercent.classList.toggle('negative', summary.comparative_data.orders_change_percent < 0);

        // Renderiza Sparklines (dados de vendas ao longo do tempo)
        // Usamos salesTimeData que contém 'total_sales' e 'num_orders'
        renderSparkline(sparklineSalesCtx, salesTimeData.map(d => d.total_sales));
        renderSparkline(sparklineOrdersCtx, salesTimeData.map(d => d.num_orders));
    }

    /**
     * Renderiza um sparkline em um canvas.
     * @param {CanvasRenderingContext2D} ctx - Contexto do canvas.
     * @param {Array<number>} data - Array de números para o sparkline.
     */
    function renderSparkline(ctx, data) {
        destroyChart(ctx.$chart); // Destrói sparkline anterior se existir

        const colors = getChartColors();

        ctx.$chart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: Array.from({length: data.length}, (_, i) => i + 1), // Rótulos simples para sparkline
                datasets: [{
                    data: data,
                    borderColor: colors.sparklineLine,
                    borderWidth: 1.5,
                    fill: true,
                    backgroundColor: colors.sparklineFill, // Gradiente suave
                    tension: 0.4, // Curva da linha
                    pointRadius: 0, // Não mostrar pontos
                    pointHitRadius: 0,
                    pointHoverRadius: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false },
                    datalabels: { display: false }
                },
                scales: {
                    x: { display: false },
                    y: { display: false }
                },
                layout: {
                    padding: { top: 5, bottom: 5, left: 5, right: 5 }
                },
                elements: {
                    line: {
                        borderColor: colors.sparklineLine
                    }
                }
            }
        });
    }


    // --- Renderização de Gráficos Principais (Chart.js) ---

    /**
     * Retorna um objeto com as cores para os gráficos, dependendo do tema atual.
     * Verifica se o corpo tem a classe 'dark-theme'.
     */
    function getChartColors() {
        const isDarkTheme = document.body.classList.contains('dark-theme');
        return {
            axisLine: isDarkTheme ? '#2C3E50' : '#CCCCCC',
            gridLine: isDarkTheme ? '#1e272f' : '#E0E0E0',
            fontColor: isDarkTheme ? '#E0E6F0' : '#333333',
            tooltipBg: isDarkTheme ? 'rgba(13, 17, 23, 0.9)' : 'rgba(255, 255, 255, 0.9)',
            tooltipBorder: isDarkTheme ? '#00EEFF' : '#007BFF',
            tooltipFont: isDarkTheme ? '#E0E6F0' : '#333333',
            barBg: isDarkTheme ? '#00EEFF' : '#007BFF', // Cor principal para barras
            lineBorder: isDarkTheme ? '#00EEFF' : '#007BFF', // Cor principal para linhas
            lineFill: isDarkTheme ? 'rgba(0, 238, 255, 0.1)' : 'rgba(0, 123, 255, 0.2)', // Preenchimento suave
            // Cores para gráficos de rosca/pizza (gradiente ou ciclo de cores neon)
            doughnutColors: isDarkTheme ? [
                '#00EEFF', '#39FF14', '#A020F0', '#FF3366', '#00CCFF', '#8A2BE2', '#32CD32', '#66FFFF'
            ] : [
                '#007BFF', '#28A745', '#FFC107', '#DC3545', '#6F42C1', '#20C997', '#FD7E14', '#17A2B8'
            ],
            sparklineLine: isDarkTheme ? '#00EEFF' : '#007BFF',
            sparklineFill: isDarkTheme ? 'rgba(0, 238, 255, 0.05)' : 'rgba(0, 123, 255, 0.1)'
        };
    }

    /**
     * Renderiza todos os gráficos do dashboard.
     * @param {Array} productsData - Dados de produtos.
     * @param {Array} categoriesData - Dados de categorias.
     * @param {Array} salesTimeData - Dados de vendas ao longo do tempo.
     * @param {Array} paymentMethodsData - Dados de tipo de conta.
     * @param {Array} salesStatusData - Dados de status de pedido.
     * @param {Array} regionData - Dados de transportadora.
     */
    function renderCharts(productsData, categoriesData, salesTimeData, paymentMethodsData, salesStatusData, regionData) {
        const colors = getChartColors();

        // Destroi gráficos existentes antes de recriá-los
        destroyChart(salesOverTimeChart);
        destroyChart(topProductsChart);
        destroyChart(topCategoriesChart);
        destroyChart(paymentMethodsChart);
        destroyChart(salesStatusChart);
        destroyChart(salesByRegionChart);

        // --- Gráfico de Vendas Totais ao Longo do Tempo (Linha) ---
        salesOverTimeChart = new Chart(salesOverTimeCtx, {
            type: 'line',
            data: {
                labels: salesTimeData.map(d => d.date),
                datasets: [{
                    label: 'Vendas Totais (R$)',
                    data: salesTimeData.map(d => d.total_sales),
                    borderColor: colors.lineBorder,
                    backgroundColor: colors.lineFill,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: colors.lineBorder,
                    pointBorderColor: colors.fontColor,
                    pointRadius: 3,
                    pointHoverRadius: 5
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        labels: { color: colors.fontColor }
                    },
                    tooltip: {
                        backgroundColor: colors.tooltipBg,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 1,
                        titleColor: colors.tooltipFont,
                        bodyColor: colors.tooltipFont,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                if (context.parsed.y !== null) label += formatCurrency(context.parsed.y);
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: colors.gridLine },
                        ticks: { color: colors.fontColor },
                        title: { display: true, text: 'Data', color: colors.fontColor }
                    },
                    y: {
                        grid: { color: colors.gridLine },
                        ticks: {
                            color: colors.fontColor,
                            callback: function(value) { return formatCurrency(value); }
                        },
                        title: { display: true, text: 'Valor (R$)', color: colors.fontColor }
                    }
                }
            }
        });

        // --- Gráfico de Top Produtos por Venda (Barras) ---
        topProductsChart = new Chart(topProductsCtx, {
            type: 'bar',
            data: {
                labels: productsData.map(d => d.nome_item),
                datasets: [{
                    label: 'Vendas (R$)',
                    data: productsData.map(d => d.total_value),
                    backgroundColor: colors.barBg,
                    borderColor: colors.lineBorder,
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: colors.tooltipBg,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 1,
                        titleColor: colors.tooltipFont,
                        bodyColor: colors.tooltipFont,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                if (context.parsed.y !== null) label += formatCurrency(context.parsed.y);
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: colors.fontColor }
                    },
                    y: {
                        grid: { color: colors.gridLine },
                        ticks: {
                            color: colors.fontColor,
                            callback: function(value) { return formatCurrency(value); }
                        },
                        beginAtZero: true
                    }
                }
            }
        });

        // --- Gráfico de Vendas por Categoria (Barras) ---
        topCategoriesChart = new Chart(topCategoriesCtx, {
            type: 'bar',
            data: {
                labels: categoriesData.map(d => d.categoria_produto),
                datasets: [{
                    label: 'Vendas (R$)',
                    data: categoriesData.map(d => d.total_value),
                    backgroundColor: colors.doughnutColors[1], // Usa uma cor diferente do ciclo
                    borderColor: colors.doughnutColors[1],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: colors.tooltipBg,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 1,
                        titleColor: colors.tooltipFont,
                        bodyColor: colors.tooltipFont,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                if (context.parsed.y !== null) label += formatCurrency(context.parsed.y);
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { color: colors.fontColor }
                    },
                    y: {
                        grid: { color: colors.gridLine },
                        ticks: {
                            color: colors.fontColor,
                            callback: function(value) { return formatCurrency(value); }
                        },
                        beginAtZero: true
                    }
                }
            }
        });

        // --- Gráfico de Vendas por Tipo de Conta (Doughnut) ---
        paymentMethodsChart = new Chart(paymentMethodsCtx, {
            type: 'doughnut',
            data: {
                labels: paymentMethodsData.map(d => d.tipo_conta), // Usa 'tipo_conta'
                datasets: [{
                    label: 'Vendas (R$)',
                    data: paymentMethodsData.map(d => d.total_value),
                    backgroundColor: colors.doughnutColors,
                    borderColor: colors.bgSecondary, // Borda para separar as fatias
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: colors.fontColor }
                    },
                    tooltip: {
                        backgroundColor: colors.tooltipBg,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 1,
                        titleColor: colors.tooltipFont,
                        bodyColor: colors.tooltipFont,
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) label += ': ';
                                if (context.parsed !== null) label += formatCurrency(context.parsed) + ' (' + formatPercentage(context.dataset.data.reduce((a, b) => a + b, 0) > 0 ? (context.parsed / context.dataset.data.reduce((a, b) => a + b, 0)) * 100 : 0) + ')';
                                return label;
                            }
                        }
                    }
                }
            }
        });

        // --- Gráfico de Vendas por Status de Pedido (Doughnut) ---
        salesStatusChart = new Chart(salesStatusCtx, {
            type: 'doughnut',
            data: {
                labels: salesStatusData.map(d => d.status_pedido), // Usa 'status_pedido'
                datasets: [{
                    label: 'Número de Pedidos',
                    data: salesStatusData.map(d => d.num_orders),
                    backgroundColor: colors.doughnutColors,
                    borderColor: colors.bgSecondary,
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'right',
                        labels: { color: colors.fontColor }
                    },
                    tooltip: {
                        backgroundColor: colors.tooltipBg,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 1,
                        titleColor: colors.tooltipFont,
                        bodyColor: colors.tooltipFont,
                        callbacks: {
                            label: function(context) {
                                let label = context.label || '';
                                if (label) label += ': ';
                                if (context.parsed !== null) label += context.parsed.toLocaleString('pt-BR') + ' pedidos';
                                return label;
                            }
                        }
                    }
                }
            }
        });

        // --- Gráfico de Vendas por Transportadora (Barras Horizontais) ---
        salesByRegionChart = new Chart(salesByRegionCtx, {
            type: 'bar',
            data: {
                labels: regionData.map(d => d.transportadora), // Usa 'transportadora'
                datasets: [{
                    label: 'Vendas (R$)',
                    data: regionData.map(d => d.total_value),
                    backgroundColor: colors.doughnutColors[2], // Outra cor do ciclo
                    borderColor: colors.doughnutColors[2],
                    borderWidth: 1
                }]
            },
            options: {
                indexAxis: 'y', // Barras horizontais
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        backgroundColor: colors.tooltipBg,
                        borderColor: colors.tooltipBorder,
                        borderWidth: 1,
                        titleColor: colors.tooltipFont,
                        bodyColor: colors.tooltipFont,
                        callbacks: {
                            label: function(context) {
                                let label = context.dataset.label || '';
                                if (label) label += ': ';
                                if (context.parsed.x !== null) label += formatCurrency(context.parsed.x);
                                return label;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { color: colors.gridLine },
                        ticks: {
                            color: colors.fontColor,
                            callback: function(value) { return formatCurrency(value); }
                        },
                        beginAtZero: true
                    },
                    y: {
                        grid: { display: false },
                        ticks: { color: colors.fontColor }
                    }
                }
            }
        });
    }

    // --- Atualização da Tabela de Vendas Recentes ---

    /**
     * Popula a tabela de vendas recentes com os dados.
     * @param {Array<object>} recentSales - Lista de objetos de vendas recentes.
     */
    function updateRecentSalesTable(recentSales) {
        recentSalesTbody.innerHTML = ''; // Limpa a tabela

        if (recentSales.length === 0) {
            recentSalesTbody.innerHTML = '<tr><td colspan="5" class="data-placeholder-row">Nenhuma venda encontrada para o período.</td></tr>';
            return;
        }

        recentSales.forEach(sale => {
            const row = document.createElement('tr');
            const saleDate = new Date(sale.data); // Usando a coluna 'data'
            row.innerHTML = `
                <td>${sale.pedido_id}</td>
                <td>${saleDate.toLocaleString('pt-BR')}</td>
                <td>${sale.nome_item}</td>
                <td>${formatCurrency(sale.valor_total)}</td>
                <td class="status-${sale.status_pedido.replace(/\s/g, '')}">${sale.status_pedido}</td>
            `;
            recentSalesTbody.appendChild(row);
        });
    }

    // --- Lógica de Filtros e Tema ---

    /**
     * Alterna a visibilidade dos campos de data personalizados.
     */
    function toggleCustomDateInputs() {
        if (periodSelect.value === 'custom') {
            startDateInput.style.display = 'inline-block';
            endDateInput.style.display = 'inline-block';
        } else {
            startDateInput.style.display = 'none';
            endDateInput.style.display = 'none';
        }
    }

    /**
     * Alterna o tema entre claro e escuro e salva a preferência.
     * Sincronizado com a classe 'dark-theme' do base.html.
     */
    function toggleTheme() {
        // Toggle a classe 'dark-theme' no body
        document.body.classList.toggle('dark-theme');
        const isDarkTheme = document.body.classList.contains('dark-theme');
        localStorage.setItem('theme', isDarkTheme ? 'dark' : 'light');

        // Atualiza a visibilidade dos ícones de sol/lua
        if (isDarkTheme) {
            lightIcon.style.display = 'none';
            darkIcon.style.display = 'inline-block';
        } else {
            lightIcon.style.display = 'inline-block';
            darkIcon.style.display = 'none';
        }

        // Re-renderiza gráficos para aplicar novas cores do tema
        // Recupera os dados atuais para evitar uma nova requisição completa
        const currentSalesTimeData = salesOverTimeChart ? salesOverTimeChart.data.labels.map((label, idx) => ({ date: label, total_sales: salesOverTimeChart.data.datasets[0].data[idx], num_orders: salesOverTimeChart.data.datasets[0].data[idx] /* simplificado, idealmente viria do estado */ })) : [];
        const currentProductsData = topProductsChart ? topProductsChart.data.labels.map((label, idx) => ({ nome_item: label, total_value: topProductsChart.data.datasets[0].data[idx] })) : [];
        const currentCategoriesData = topCategoriesChart ? topCategoriesChart.data.labels.map((label, idx) => ({ categoria_produto: label, total_value: topCategoriesChart.data.datasets[0].data[idx] })) : [];
        const currentPaymentMethodsData = paymentMethodsChart ? paymentMethodsChart.data.labels.map((label, idx) => ({ tipo_conta: label, total_value: paymentMethodsChart.data.datasets[0].data[idx] })) : [];
        const currentSalesStatusData = salesStatusChart ? salesStatusChart.data.labels.map((label, idx) => ({ status_pedido: label, num_orders: salesStatusChart.data.datasets[0].data[idx] })) : [];
        const currentRegionData = salesByRegionChart ? salesByRegionChart.data.labels.map((label, idx) => ({ transportadora: label, total_value: salesByRegionChart.data.datasets[0].data[idx] })) : [];


        renderCharts(
            currentProductsData,
            currentCategoriesData,
            currentSalesTimeData,
            currentPaymentMethodsData,
            currentSalesStatusData,
            currentRegionData
        );
        // Para os sparklines, também é necessário recriar com as novas cores
        const currentSparklineSalesData = sparklineSalesCtx.$chart ? sparklineSalesCtx.$chart.data.datasets[0].data : [];
        const currentSparklineOrdersData = sparklineOrdersCtx.$chart ? sparklineOrdersCtx.$chart.data.datasets[0].data : [];
        renderSparkline(sparklineSalesCtx, currentSparklineSalesData);
        renderSparkline(sparklineOrdersCtx, currentSparklineOrdersData);
    }

    // --- Event Listeners ---

    periodSelect.addEventListener('change', () => {
        toggleCustomDateInputs();
        fetchDashboardData(); // Recarrega os dados ao mudar o período
    });

    startDateInput.addEventListener('change', fetchDashboardData);
    endDateInput.addEventListener('change', fetchDashboardData);

    refreshButton.addEventListener('click', fetchDashboardData);
    themeToggleButton.addEventListener('click', toggleTheme);

    // --- Inicialização ---

    /**
     * Função de inicialização do dashboard.
     */
    function initializeDashboard() {
        // Carrega a preferência de tema do localStorage e aplica a classe 'dark-theme' se necessário
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme === 'dark') {
            document.body.classList.add('dark-theme');
            lightIcon.style.display = 'none';
            darkIcon.style.display = 'inline-block';
        } else {
            document.body.classList.remove('dark-theme');
            lightIcon.style.display = 'inline-block';
            darkIcon.style.display = 'none';
        }

        toggleCustomDateInputs(); // Inicializa a visibilidade das datas personalizadas
        lucide.createIcons(); // Inicializa os ícones do Lucide
        fetchDashboardData(); // Carrega os dados iniciais

        // Configura atualização automática a cada 5 minutos (300000 ms)
        setInterval(fetchDashboardData, 300000);
    }

    initializeDashboard(); // Chama a função de inicialização quando o DOM estiver carregado
});
