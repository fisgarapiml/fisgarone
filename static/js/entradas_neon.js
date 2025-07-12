document.addEventListener('DOMContentLoaded', function() {
    // Inicializar máscaras de data
    if (typeof Inputmask !== 'undefined') {
        Inputmask('99/99/9999').mask('.date-mask');
    }

    // Formatter para moeda BRL
    const currencyFormatter = new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    });

    // Função para converter data frontend (DD/MM/YYYY) para SQL (YYYY-MM-DD)
    function convertToSQLDate(dateStr) {
        if (!dateStr) return '';

        // Se já está no formato YYYY-MM-DD
        if (dateStr.match(/^\d{4}-\d{2}-\d{2}$/)) {
            return dateStr;
        }

        // Converte de DD/MM/YYYY para YYYY-MM-DD
        const [day, month, year] = dateStr.split('/');
        return `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;
    }

    // Função principal para buscar dados
    function buscarDados() {
        const form = document.getElementById('filtros-entradas');
        const formData = new FormData(form);
        const params = new URLSearchParams();

        // Processar cada campo do formulário
        formData.forEach((value, key) => {
            if (value) {
                // Converter datas para formato SQL
                if (key === 'data_ini' || key === 'data_fim') {
                    params.append(key, convertToSQLDate(value));
                } else {
                    params.append(key, value);
                }
            }
        });

        // Mostrar estado de loading
        const cardsContainer = document.getElementById('cards-container');
        if (cardsContainer) {
            cardsContainer.classList.add('loading');
        }

        fetch(`/financeiro/entradas/dados?${params.toString()}`)
            .then(response => {
                if (!response.ok) throw new Error('Erro na requisição');
                return response.json();
            })
            .then(data => {
                // Atualizar todos os componentes da interface
                atualizarCards(data.cards);
                renderEvolucaoChart(data.evolucao);
                renderCanalChart(data.pizza);
                atualizarTabela(data.entradas);
            })
            .catch(error => {
                console.error('Erro ao buscar dados:', error);
                alert('Erro ao carregar dados. Tente novamente.');
            })
            .finally(() => {
                if (cardsContainer) {
                    cardsContainer.classList.remove('loading');
                }
            });
    }

    // Atualizar cards com animação
    function atualizarCards(cards) {
        if (!cards || !Array.isArray(cards)) return;

        cards.forEach((card, index) => {
            const cardElement = document.querySelector(`.financeiro-card:nth-child(${index + 1}) .card-value`);
            if (cardElement) {
                animateValue(cardElement, 0, card.value, 1000);
            }
        });
    }

    // Animação de contagem nos valores
    function animateValue(element, start, end, duration) {
        let startTimestamp = null;
        const step = (timestamp) => {
            if (!startTimestamp) startTimestamp = timestamp;
            const progress = Math.min((timestamp - startTimestamp) / duration, 1);
            const value = Math.floor(progress * (end - start) + start);
            element.textContent = currencyFormatter.format(value);
            if (progress < 1) {
                window.requestAnimationFrame(step);
            }
        };
        window.requestAnimationFrame(step);
    }

    // Renderizar gráfico de evolução
    function renderEvolucaoChart(evolucaoData) {
        const ctx = document.getElementById('evolucaoChart');
        if (!ctx) return;

        // Destruir gráfico anterior se existir
        if (window.evolucaoChartObj) {
            window.evolucaoChartObj.destroy();
        }

        window.evolucaoChartObj = new Chart(ctx.getContext('2d'), {
            type: 'line',
            data: {
                labels: evolucaoData.labels || [],
                datasets: [{
                    label: 'Valor Recebido',
                    data: evolucaoData.data || [],
                    borderColor: '#4e73df',
                    backgroundColor: 'rgba(78, 115, 223, 0.05)',
                    borderWidth: 2,
                    tension: 0.3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: ctx => currencyFormatter.format(ctx.raw)
                        }
                    },
                    legend: { display: false }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: value => currencyFormatter.format(value)
                        }
                    }
                }
            }
        });
    }

    // Renderizar gráfico de pizza por canal
    function renderCanalChart(pizzaData) {
        const ctx = document.getElementById('canalChart');
        if (!ctx) return;

        // Destruir gráfico anterior se existir
        if (window.canalChartObj) {
            window.canalChartObj.destroy();
        }

        window.canalChartObj = new Chart(ctx.getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: pizzaData.labels || [],
                datasets: [{
                    data: pizzaData.data || [],
                    backgroundColor: ['#4e73df', '#1cc88a', '#36b9cc', '#f6c23e'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: context => {
                                const label = context.label || '';
                                const value = context.raw || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = total > 0 ? Math.round((value / total) * 100) : 0;
                                return `${label}: ${currencyFormatter.format(value)} (${percentage}%)`;
                            }
                        }
                    },
                    legend: {
                        position: 'right',
                        labels: {
                            usePointStyle: true,
                            padding: 20
                        }
                    }
                },
                cutout: '70%'
            }
        });
    }

    // Atualizar tabela de entradas
    function atualizarTabela(entradas) {
        const tbody = document.querySelector('.tabela-wrapper tbody');
        if (!tbody) return;

        // Limpar tabela
        tbody.innerHTML = '';

        // Mensagem para dados vazios
        if (!entradas || entradas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" class="no-data">Nenhuma entrada encontrada para os filtros selecionados</td></tr>';
            return;
        }

        // Popular tabela com novos dados
        entradas.forEach(e => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${e.data || '--'}</td>
                <td><span class="badge ${(e.canal || '').toLowerCase().replace(' ', '-')}">${e.canal || '--'}</span></td>
                <td>${e.pedido_id || '--'}</td>
                <td>${currencyFormatter.format(e.valor || 0)}</td>
                <td><span class="status ${(e.status || '').toLowerCase()}">${e.status || '--'}</span></td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Evento de submit do formulário
    const filtrosForm = document.getElementById('filtros-entradas');
    if (filtrosForm) {
        filtrosForm.addEventListener('submit', function(e) {
            e.preventDefault();
            buscarDados();
        });
    }

    // Buscar dados iniciais ao carregar a página
    buscarDados();
});