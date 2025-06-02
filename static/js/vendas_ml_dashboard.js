window.vendasDiaChartInstance = null;
window.top10ChartInstance = null;

document.addEventListener("DOMContentLoaded", function() {
    const vendasDiaLabels = window.vendasDiaLabels;
    const vendasDiaData = window.vendasDiaData;
    const vendasDiaAntData = window.vendasDiaAntData;

    // -- GRÁFICO DE VENDAS DIÁRIAS --
    if (document.getElementById('vendasDiaChart')) {
        const ctxVendasDia = document.getElementById('vendasDiaChart').getContext('2d');
        if (window.vendasDiaChartInstance) window.vendasDiaChartInstance.destroy();
        window.vendasDiaChartInstance = new Chart(ctxVendasDia, {
            type: 'bar',
            data: {
                labels: vendasDiaLabels,
                datasets: [
                    {
                        label: 'Faturamento Atual',
                        data: vendasDiaData,
                        backgroundColor: "#1259c3",
                        borderRadius: 12,
                        maxBarThickness: 28,
                        yAxisID: 'y',
                        datalabels: {
                            color: '#fff500',
                            backgroundColor: '#1259c3cc',
                            borderRadius: 8,
                            font: { weight: 'bold', size: 15 },
                            anchor: 'end',
                            align: 'end',
                            offset: 2,
                            formatter: value => Math.round(value).toLocaleString('pt-BR'),
                            padding: 5,
                            display: ctx => ctx.dataset.data[ctx.dataIndex] > 0
                        }
                    },
                 {
    label: 'Mês Anterior',
    data: window.vendasDiaAntData,
    type: 'line',
    borderColor: "#FFA500",
    backgroundColor: "#FFA500",
    borderWidth: 2.5,
    fill: false,
    pointRadius: 6,
    pointBackgroundColor: "#FFA500",
    tension: 0.25,
    yAxisID: 'y',
    datalabels: {
        color: '#FFA500',
        backgroundColor: null,
        borderRadius: 0,
        font: { weight: 'bold', size: 14 },
        anchor: 'end',      // <<< OBRIGATÓRIO
        align: 'bottom',    // <<< OBRIGATÓRIO
        offset: 32,         // <<< QUANTO MAIOR MAIS PRA BAIXO
        clip: false,
        formatter: value => Math.round(value).toLocaleString('pt-BR'),
        padding: 2,
        display: ctx => ctx.dataset.data[ctx.dataIndex] > 0
    }
}

                ]
            },
            options: {
                plugins: {
                    legend: { display: true }
                },
                scales: {
                    x: { grid: { color: '#e0f7fa33' } },
                    y: { grid: { color: '#e0f7fa22' } }
                }
            },
            plugins: [ChartDataLabels]
        });
    }

    // -- TOP 10 SKUs --
    const top10Labels = window.top10Labels;
    const top10Data = window.top10Data;
    if (document.getElementById('top10Chart')) {
        const ctxTop10 = document.getElementById('top10Chart').getContext('2d');
        if (window.top10ChartInstance) window.top10ChartInstance.destroy();
        window.top10ChartInstance = new Chart(ctxTop10, {
            type: 'bar',
            data: {
                labels: top10Labels,
                datasets: [{
                    label: 'Unidades',
                    data: top10Data,
                    backgroundColor: "#fff500",
                    borderRadius: 12,
                    maxBarThickness: 28
                }]
            },
            options: {
                indexAxis: 'y',
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        color: '#1259c3',
                        backgroundColor: '#fff500cc',
                        borderRadius: 8,
                        font: { weight: 'bold', size: 15 },
                        anchor: 'center',
                        align: 'center',
                        formatter: function(value) {
                            return Math.round(value).toLocaleString('pt-BR');
                        },
                        padding: 5,
                        display: function(ctx) {
                            return ctx.dataset.data[ctx.dataIndex] > 0;
                        }
                    }
                },
                scales: {
                    x: { grid: { color: '#e0f7fa33' }, ticks: { color: '#1259c3', font: { weight: 700 } } },
                    y: { grid: { color: '#e0f7fa22' }, ticks: { color: '#1259c3', font: { weight: 700 } } }
                },
                onClick: function(evt, elements) {
                    if (elements.length > 0) {
                        let sku = this.data.labels[elements[0].index];
                        if (typeof abrirModalFiltro === 'function') {
                            abrirModalFiltro(sku);
                        }
                    }
                }
            },
            plugins: [ChartDataLabels]
        });
    }
});
