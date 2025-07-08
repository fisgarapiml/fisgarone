document.addEventListener('DOMContentLoaded', function() {
    // Utilitário para moeda BRL
    const currencyFormatter = new Intl.NumberFormat('pt-BR', {
        style: 'currency',
        currency: 'BRL'
    });

    // Função para buscar e atualizar dados do dashboard
    function buscarDados() {
        // Coleta filtros do formulário
        const params = new URLSearchParams();
        const form = document.getElementById('filtros-entradas');
        if (form) {
            Array.from(form.elements).forEach(el => {
                if (el.name && el.value) {
                    params.append(el.name, el.value);
                }
            });
        }

        fetch('/financeiro/entradas/dados?' + params.toString())
            .then(response => response.json())
            .then(data => {
                atualizarCards(data.consolidado);
                renderEvolucaoChart(data.evolucao);
                renderCanalChart(data.consolidado);
                atualizarTabela(data.entradas);
            })
            .catch(error => console.error('Erro:', error));
    }

    // Animação dos valores nos cards
    function atualizarCards(consolidado) {
        const cardTitles = [
            'Entradas Totais', 'A Receber', 'Mercado Livre', 'Shopee', 'Recebido Hoje'
        ];
        document.querySelectorAll('.financeiro-card').forEach((card, i) => {
            let value = 0;
            switch (cardTitles[i]) {
                case 'Entradas Totais': value = consolidated.recebido || 0; break;
                case 'A Receber': value = consolidated.pendente || 0; break;
                case 'Mercado Livre': value = consolidated.ml || 0; break;
                case 'Shopee': value = consolidated.shopee || 0; break;
                case 'Recebido Hoje': value = consolidated.hoje || 0; break;
            }
            const el = card.querySelector('.card-value');
            let start = 0, end = value, duration = 1000, startTime = performance.now();
            const animate = currentTime => {
                const elapsed = currentTime - startTime;
                const progress = Math.min(elapsed / duration, 1);
                const currentValue = progress * end;
                el.textContent = currencyFormatter.format(currentValue);
                if (progress < 1) requestAnimationFrame(animate);
            };
            requestAnimationFrame(animate);
        });
    }

    // Gráfico de Evolução
    function renderEvolucaoChart(evolucaoData) {
        const ctx = document.getElementById('evolucaoChart').getContext('2d');
        if (window.evolucaoChartObj) window.evolucaoChartObj.destroy();
        const labels = evolucaoData.map(item => item.data);
        const valores = evolucaoData.map(item => item.total);
        window.evolucaoChartObj = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Valor Recebido',
                    data: valores,
                    borderColor: '#3498db',
                    backgroundColor: 'rgba(52, 152, 219, 0.1)',
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

    // Gráfico de Canais
    function renderCanalChart(consolidadoData) {
        const ctx = document.getElementById('canalChart').getContext('2d');
        if (window.canalChartObj) window.canalChartObj.destroy();
        window.canalChartObj = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Mercado Livre', 'Shopee'],
                datasets: [{
                    data: [consolidadoData.ml || 0, consolidadoData.shopee || 0],
                    backgroundColor: ['#ffe600', '#ee4d2d'],
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
                    legend: { position: 'right' }
                },
                cutout: '70%'
            }
        });
    }

    // Atualiza a tabela de entradas
    function atualizarTabela(entradas) {
        const tbody = document.querySelector('.tabela-container tbody');
        if (!tbody) return;
        tbody.innerHTML = '';
        if (!entradas || entradas.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5">Sem entradas para os filtros selecionados.</td></tr>';
            return;
        }
        entradas.forEach(e => {
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td>${e.data}</td>
                <td><span class="badge ${e.canal.toLowerCase().replace(' ', '-')}">${e.canal}</span></td>
                <td>${e.pedido_id}</td>
                <td>R$ ${currencyFormatter.format(e.valor).replace('R$', '')}</td>
                <td><span class="status ${e.status.toLowerCase()}">${e.status}</span></td>
            `;
            tbody.appendChild(tr);
        });
    }

    // Dispara busca inicial (padrão mês atual) e ao aplicar filtros
    buscarDados();
    const form = document.getElementById('filtros-entradas');
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            buscarDados();
        });
    }
});

   document.addEventListener('DOMContentLoaded', function() {
    // ... Outros códigos aqui

    document.getElementById('filtros-entradas').addEventListener('submit', function(e) {
        e.preventDefault(); // Evita reload da página

        // Pegando valores dos filtros
        const dataIni = document.getElementById('data_ini').value;
        const dataFim = document.getElementById('data_fim').value;
        const canal = document.getElementById('canal').value;
        const status = document.getElementById('status').value;
        const pedidoId = document.getElementById('pedido_id').value;

        // Monta a query string
        const params = new URLSearchParams({
            data_ini: dataIni,
            data_fim: dataFim,
            canal: canal,
            status: status,
            pedido_id: pedidoId
        });

        fetch(`/financeiro/entradas/dados?${params.toString()}`)
            .then(response => response.json())
            .then(data => {
                // Aqui atualize os cards, gráficos, tabela etc
                // EXEMPLO:
                renderEvolucaoChart(data.evolucao);
                renderCanalChart(data.consolidado);

                // Atualizar cards
                document.querySelectorAll('.financeiro-card').forEach((el, i) => {
                    const cardValue = el.querySelector('.card-value');
                    if (cardValue && data.cards && data.cards[i]) {
                        cardValue.textContent = 'R$ ' + parseFloat(data.cards[i].value).toLocaleString('pt-BR', {minimumFractionDigits: 2});
                    }
                });

                // Atualizar tabela
                const tbody = document.querySelector('.tabela-wrapper tbody');
                if (tbody) {
                    tbody.innerHTML = '';
                    data.entradas.forEach(e => {
                        tbody.innerHTML += `<tr>
                            <td>${e.data}</td>
                            <td><span class="badge ${e.canal.toLowerCase()}">${e.canal}</span></td>
                            <td>${e.pedido_id}</td>
                            <td>R$ ${parseFloat(e.valor).toLocaleString('pt-BR', {minimumFractionDigits: 2})}</td>
                            <td><span class="status ${e.status.toLowerCase()}">${e.status}</span></td>
                        </tr>`;
                    });
                }
            });
    });
});


    // Evento do botão
    document.getElementById('btn-filtrar').addEventListener('click', function(e) {
        e.preventDefault();
        atualizarDashboardComFiltros();
    });
});
