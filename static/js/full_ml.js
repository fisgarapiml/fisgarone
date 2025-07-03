// Função para inicializar todos os gráficos
function initializeCharts(salesData, dailySalesData, productsStatusData, topProductsData) {
    // Gráfico de Vendas Mensais
    const salesCtx = document.getElementById('salesChart').getContext('2d');
    const salesChart = new Chart(salesCtx, {
        type: 'line',
        data: {
            labels: salesData.map(item => item[0]),
            datasets: [{
                label: 'Faturamento (R$)',
                data: salesData.map(item => item[1]),
                borderColor: '#00c8ff',
                backgroundColor: 'rgba(0, 200, 255, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        callback: function(value) {
                            return 'R$ ' + value.toLocaleString();
                        }
                    }
                },
                x: {
                    grid: {
                        display: false
                    }
                }
            }
        }
    });

    // Gráfico de Status dos Anúncios
    const productsStatusCtx = document.getElementById('productsStatusChart').getContext('2d');
    const productsStatusChart = new Chart(productsStatusCtx, {
        type: 'doughnut',
        data: {
            labels: productsStatusData.map(item => item[0]),
            datasets: [{
                data: productsStatusData.map(item => item[1]),
                backgroundColor: [
                    '#00c8ff',
                    '#0095ff',
                    '#0066ff',
                    '#0033ff',
                    '#0000ff'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            },
            cutout: '70%'
        }
    });

    // Gráfico de Conversão
    const conversionCtx = document.getElementById('conversionChart').getContext('2d');
    const conversionChart = new Chart(conversionCtx, {
        type: 'bar',
        data: {
            labels: dailySalesData.map(item => item[0]),
            datasets: [{
                label: 'Taxa de Conversão (%)',
                data: dailySalesData.map(item => (Math.random() * 10 + 5).toFixed(1)),
                backgroundColor: 'rgba(0, 200, 255, 0.7)',
                borderColor: 'rgba(0, 200, 255, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    max: 15,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            }
        }
    });

    // Gráfico de Visitas
    const visitsCtx = document.getElementById('visitsChart').getContext('2d');
    const visitsChart = new Chart(visitsCtx, {
        type: 'line',
        data: {
            labels: dailySalesData.map(item => item[0]),
            datasets: [{
                label: 'Visitas',
                data: dailySalesData.map(item => Math.floor(Math.random() * 100 + 50)),
                borderColor: '#0095ff',
                backgroundColor: 'rgba(0, 149, 255, 0.1)',
                borderWidth: 2,
                tension: 0.4,
                fill: true
            }]
        },
        options: {
            responsive: true,
            plugins: {
                legend: {
                    display: false
                }
            }
        }
    });
}

// Atualização de dados via AJAX
$(document).ready(function() {
    // Extrai o nome da conta do caminho da URL
    const pathParts = window.location.pathname.split('/');
    const accountName = pathParts[pathParts.length - 1];

    // Configura o botão de atualização
    $('#refresh-data').click(function() {
        const loadingModal = new bootstrap.Modal(document.getElementById('loadingModal'));
        loadingModal.show();

        $.ajax({
            url: `/api/full_ml/${accountName}/refresh`,
            method: 'GET',
            success: function(response) {
                if (response.status === 'success') {
                    // Recarrega os dados após atualização
                    $.ajax({
                        url: `/api/full_ml/${accountName}/data`,
                        method: 'GET',
                        success: function(data) {
                            // Atualiza as métricas rápidas
                            if (data.metrics) {
                                $('#total-sales').text(data.metrics.total_sales.toFixed(2));
                                $('#total-orders').text(data.metrics.total_orders);
                                $('#avg-order').text(data.metrics.avg_order_value.toFixed(2));
                                $('#conversion-rate').text(data.metrics.conversion_rate.toFixed(1));
                            }

                            // Mostra mensagem de sucesso
                            showAlert('Dados atualizados com sucesso!', 'success');
                        },
                        error: function() {
                            showAlert('Erro ao carregar dados atualizados', 'danger');
                        },
                        complete: function() {
                            loadingModal.hide();
                        }
                    });
                } else {
                    showAlert(response.message, 'danger');
                    loadingModal.hide();
                }
            },
            error: function(xhr) {
                const errorMsg = xhr.responseJSON ? xhr.responseJSON.message : 'Erro na comunicação com o servidor';
                showAlert(errorMsg, 'danger');
                loadingModal.hide();
            }
        });
    });

    // Função para mostrar alertas
    function showAlert(message, type) {
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        $('#alerts-container').html(alertHtml);

        // Remove o alerta após 5 segundos
        setTimeout(() => {
            $('.alert').alert('close');
        }, 5000);
    }

    // Tooltips
    $('[data-bs-toggle="tooltip"]').tooltip();
});