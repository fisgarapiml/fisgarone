document.addEventListener("DOMContentLoaded", function() {
    // Top 10 SKUs Vendidos
    const top10Labels = {{ top10['sku'].tolist()|tojson }};
    const top10Data = {{ top10['quantity'].tolist()|tojson }};
    if (document.getElementById('top10Chart')) {
        new Chart(document.getElementById('top10Chart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: top10Labels,
                datasets: [{
                    label: 'Unidades Vendidas',
                    data: top10Data,
                    backgroundColor: '#00e0ff99',
                    borderColor: '#00e0ff',
                    borderWidth: 2,
                    borderRadius: 9
                }]
            },
            options: {
                responsive: true,
                indexAxis: 'y',
                plugins: { legend: { display: false }},
                scales: {
                    x: { grid: { color: '#e0f7fa33' }, ticks: { color: '#1d2547' } },
                    y: { grid: { color: '#e0f7fa22' }, ticks: { color: '#1d2547' } }
                }
            }
        });
    }

    // Pedidos por Situação
    const statusLabels = {{ status_contagem.keys()|list|tojson }};
    const statusData = {{ status_contagem.values()|list|tojson }};
    if (document.getElementById('statusChart')) {
        new Chart(document.getElementById('statusChart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: statusLabels,
                datasets: [{
                    data: statusData,
                    backgroundColor: [
                        '#00e0ff', '#7d3cff', '#ff8800', '#fff500', '#ff29b7', '#39ff14'
                    ],
                    borderWidth: 3,
                    borderColor: '#181f2b'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'bottom',
                        labels: { color: '#1d2547', font: { weight: 700 } }
                    }
                }
            }
        });
    }

    // Vendas Diárias
    const vendasDiaLabels = {{ vendas_dia['dia'].tolist()|tojson }};
    const vendasDiaData = {{ vendas_dia['quantity'].tolist()|tojson }};
    if (document.getElementById('vendasDiaChart')) {
        new Chart(document.getElementById('vendasDiaChart').getContext('2d'), {
            type: 'bar',
            data: {
                labels: vendasDiaLabels,
                datasets: [{
                    label: 'Unidades Vendidas',
                    data: vendasDiaData,
                    backgroundColor: '#7d3cff99',
                    borderColor: '#7d3cff',
                    borderWidth: 2,
                    borderRadius: 9
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false }},
                scales: {
                    x: { grid: { color: '#e0f7fa33' }, ticks: { color: '#1d2547' } },
                    y: { grid: { color: '#e0f7fa22' }, ticks: { color: '#1d2547' } }
                }
            }
        });
    }
});
