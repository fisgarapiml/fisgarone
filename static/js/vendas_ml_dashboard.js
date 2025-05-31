document.addEventListener("DOMContentLoaded", function() {
    const top10Labels = window.top10Labels;
    const top10Data = window.top10Data;
    const vendasDiaLabels = window.vendasDiaLabels;
    const vendasDiaData = window.vendasDiaData;

    // --- Vendas Diárias (BARRA VERTICAL, OCUPA 70%) ---
    if (document.getElementById('vendasDiaChart')) {
        const ctxVendasDia = document.getElementById('vendasDiaChart').getContext('2d');
        new Chart(ctxVendasDia, {
            type: 'bar',
            data: {
                labels: vendasDiaLabels,
                datasets: [{
                    label: 'Unidades',
                    data: vendasDiaData,
                    backgroundColor: "#1259c3", // Azul ML
                    borderRadius: 12,
                    maxBarThickness: 28
                }]
            },
            options: {
                plugins: {
                    legend: { display: false },
                    datalabels: {
                        color: '#fff500',
                        backgroundColor: '#1259c3cc',
                        borderRadius: 8,
                        font: { weight: 'bold', size: 15 },
                        anchor: 'center',
                        align: 'center',
                        formatter: Math.round,
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
                        let dia = this.data.labels[elements[0].index];
                        if (typeof abrirModalFiltro === 'function') {
                            abrirModalFiltro(dia);
                        }
                    }
                }
            },
            plugins: [ChartDataLabels]
        });
    }

    // --- Top 10 SKUs Vendidos (BARRA HORIZONTAL, OCUPA 30%) ---
    if (document.getElementById('top10Chart')) {
        const ctxTop10 = document.getElementById('top10Chart').getContext('2d');
        new Chart(ctxTop10, {
            type: 'bar',
            data: {
                labels: top10Labels,
                datasets: [{
                    label: 'Unidades',
                    data: top10Data,
                    backgroundColor: "#fff500", // Amarelo ML
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
                        formatter: Math.round,
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
