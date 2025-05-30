document.addEventListener('DOMContentLoaded', function() {
    // 1. Controle de Tema
    const themeToggle = document.getElementById('themeToggle');
    const currentTheme = localStorage.getItem('theme') || 'light';

    // Aplicar tema salvo
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeIcon(currentTheme);

    // Configurar toggle do tema
    themeToggle.addEventListener('click', function() {
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);
    });

    function updateThemeIcon(theme) {
        const icon = themeToggle.querySelector('i');
        icon.className = theme === 'dark' ? 'bi bi-sun-fill' : 'bi bi-moon-fill';
    }

    // 2. Controle de Modais
    const itemModal = document.getElementById('itemModal');
    const viewModal = document.getElementById('viewModal');

    // Fechar modais
    document.getElementById('closeModal')?.addEventListener('click', () => closeModal(itemModal));
    document.getElementById('btnCancelar')?.addEventListener('click', () => closeModal(itemModal));
    document.querySelector('.view-modal-close')?.addEventListener('click', () => closeModal(viewModal));

    // Fechar ao clicar fora
    [itemModal, viewModal].forEach(modal => {
        modal?.addEventListener('click', function(e) {
            if (e.target === this) closeModal(this);
        });
    });

    function closeModal(modalElement) {
        modalElement.classList.add('fade-out');
        setTimeout(() => {
            modalElement.style.display = 'none';
            modalElement.classList.remove('fade-out');
        }, 300);
    }

    // 3. Cards Neon - Abrir Modal de Visualização
    document.querySelectorAll('.neon-card').forEach(card => {
        card.addEventListener('click', function() {
            const tipo = this.getAttribute('data-card');
            fetch(`/estoque/api/itens/${tipo}`)
                .then(response => {
                    if (!response.ok) throw new Error('Erro na requisição');
                    return response.json();
                })
                .then(data => openViewModal(tipo, data))
                .catch(error => {
                    console.error('Erro ao carregar itens:', error);
                    alert('Erro ao carregar dados. Verifique o console.');
                });
        });
    });

    // 4. Modal de Visualização
    function openViewModal(tipo, itens) {
        const viewModal = document.getElementById('viewModal');
        const closeModal = document.querySelector('.view-modal-close');

        document.getElementById('viewModalTitle').textContent = getModalTitle(tipo);
        document.getElementById('modalItemContent').innerHTML = itens.length ? renderItemsGrid(itens) : '<p class="no-items">Nenhum item encontrado</p>';

        viewModal.style.display = 'block';

        closeModal.onclick = () => {
            viewModal.classList.add('fade-out');
            setTimeout(() => {
                viewModal.style.display = 'none';
                viewModal.classList.remove('fade-out');
            }, 300);
        };

        viewModal.onclick = function(e) {
            if (e.target === this) {
                this.classList.add('fade-out');
                setTimeout(() => {
                    this.style.display = 'none';
                    this.classList.remove('fade-out');
                }, 300);
            }
        };
    }

    function getModalTitle(tipo) {
        const titles = {
            'todos': 'Todos os Itens',
            'ok': 'Itens com Estoque OK',
            'baixa': 'Itens com Estoque Baixo',
            'esgotados': 'Itens Esgotados'
        };
        return titles[tipo] || 'Visualização';
    }

    function renderItemsGrid(itens) {
        return `
        <div class="item-grid">
            ${itens.map(item => `
            <div class="item-card">
                <h3>${item.nome || 'Sem nome'}</h3>
                <p><strong>Código:</strong> ${item.codigo || '-'}</p>
                <p><strong>Estoque:</strong> ${item.qtd_estoque || 0} ${item.unidade || 'UN'}</p>
                <p><strong>Status:</strong> ${getStatusBadge(item)}</p>
            </div>
            `).join('')}
        </div>`;
    }

    function getStatusBadge(item) {
        const statusInfo = {
            esgotado: { text: 'Esgotado', class: 'danger' },
            critico: { text: 'Crítico', class: 'warning' },
            ok: { text: 'OK', class: 'success' }
        };

        let status;
        if (item.qtd_estoque === 0) {
            status = statusInfo.esgotado;
        } else if (item.qtd_estoque <= (item.estoque_minimo || 0)) {
            status = statusInfo.critico;
        } else {
            status = statusInfo.ok;
        }

        return `<span class="badge badge-${status.class}">${status.text}</span>`;
    }

    // 5. Controle de Formulário
    document.getElementById('itemPreco')?.addEventListener('input', calcularMargem);
    document.getElementById('itemCusto')?.addEventListener('input', calcularMargem);

    function calcularMargem() {
        const custo = parseFloat(document.getElementById('itemCusto').value) || 0;
        const preco = parseFloat(document.getElementById('itemPreco').value) || 0;
        const margemElement = document.getElementById('itemMargem');

        if (custo > 0 && preco > 0) {
            const margem = ((preco - custo) / custo * 100).toFixed(2);
            margemElement.value = `${margem}%`;
        } else {
            margemElement.value = '0%';
        }
    }

    // 6. Botão Novo Item
    document.getElementById('btnNovoItem')?.addEventListener('click', function() {
        document.getElementById('itemForm').reset();
        document.getElementById('modalTitle').textContent = 'Novo Item';
        document.getElementById('itemId').value = 'novo';
        itemModal.style.display = 'block';
    });

    // 7. Botão Importar
    document.getElementById('btnImportar')?.addEventListener('click', function() {
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.accept = '.csv,.xlsx,.xls';

        fileInput.onchange = function(e) {
            if (e.target.files.length > 0) {
                const btn = document.getElementById('btnImportar');
                const originalHTML = btn.innerHTML;

                btn.innerHTML = '<i class="bi bi-arrow-repeat spin"></i> Importando...';
                btn.disabled = true;

                setTimeout(() => {
                    btn.innerHTML = originalHTML;
                    btn.disabled = false;
                    alert(`Arquivo "${e.target.files[0].name}" importado com sucesso!`);
                }, 1500);
            }
        };

        fileInput.click();
    });

    // 8. Carregar Itens Prioritários
    function loadPriorityItems(view = 'criticos') {
        const endpointMap = {
            criticos: '/estoque/api/itens/criticos',
            vencimento: '/estoque/api/itens/vencimento',
            lentagem: '/estoque/api/itens/lentagem'
        };

        const endpoint = endpointMap[view] || endpointMap.criticos;

        fetch(endpoint)
            .then(response => response.json())
            .then(data => {
                const container = document.getElementById('priorityItemsContainer');
                if (!container) return;

                container.innerHTML = data.map(item => `
                    <div class="priority-item">
                        <div class="priority-indicator ${getPriorityClass(item)}"></div>
                        <div class="item-info">
                            <h4>${item.nome || 'Sem nome'}</h4>
                            <p class="item-code">${item.codigo || '-'}</p>
                        </div>
                        <div class="item-stock">
                            <div class="stock-level" style="width: ${calculateStockLevel(item)}%"></div>
                            <span>${item.qtd_estoque || 0} ${item.unidade || 'UN'}</span>
                        </div>
                        <button class="action-btn" data-id="${item.id}">
                            <i class="bi bi-arrow-right-circle"></i>
                        </button>
                    </div>
                `).join('');
            })
            .catch(error => console.error('Erro ao carregar itens prioritários:', error));
    }

    function getPriorityClass(item) {
        if (item.qtd_estoque === 0) return 'critical';
        if (item.qtd_estoque <= (item.estoque_minimo || 0)) return 'warning';
        return 'info';
    }

    function calculateStockLevel(item) {
        const max = item.estoque_maximo || item.qtd_estoque || 1;
        const current = item.qtd_estoque || 0;
        return Math.min(100, (current / max) * 100);
    }

    // 9. Inicialização dos Gráficos - CORRIGIDO
    function initCharts() {
        // Verificar se o Chart.js está carregado
        if (typeof Chart === 'undefined') {
            console.error('Chart.js não está carregado!');
            return;
        }

        // Gráfico de Movimentação
        const movCtx = document.getElementById('movimentacaoChart');
        if (movCtx) {
            new Chart(movCtx, {
                type: 'bar',
                data: {
                    labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
                    datasets: [
                        {
                            label: 'Entradas',
                            data: [120, 190, 170, 220, 180, 250],
                            backgroundColor: 'rgba(0, 204, 136, 0.7)'
                        },
                        {
                            label: 'Saídas',
                            data: [80, 120, 150, 180, 140, 200],
                            backgroundColor: 'rgba(0, 102, 255, 0.7)'
                        }
                    ]
                },
                options: {
                    responsive: true,
                    scales: {
                        x: { stacked: true },
                        y: { stacked: true }
                    }
                }
            });
        } else {
            console.error('Elemento movimentacaoChart não encontrado!');
        }

        // Gráfico de Performance (adicione se necessário)
        const perfCtx = document.getElementById('performanceChart');
        if (perfCtx) {
            new Chart(perfCtx, {
                type: 'doughnut',
                data: {
                    labels: ['Disponível', 'Reservado', 'Esgotado'],
                    datasets: [{
                        data: [75, 15, 10],
                        backgroundColor: [
                            'rgba(0, 204, 136, 0.7)',
                            'rgba(0, 102, 255, 0.7)',
                            'rgba(255, 51, 102, 0.7)'
                        ]
                    }]
                }
            });
        }
    }

    // 10. Modal de Edição Avançado - CORRIGIDO
    function setupItemModal() {
        const itemModal = document.getElementById('itemModal');
        const btnNovoItem = document.getElementById('btnNovoItem');
        const btnCancelar = document.getElementById('btnCancelar');
        const closeModalBtn = document.getElementById('closeModal');

        // Abrir modal para novo item
        btnNovoItem?.addEventListener('click', function() {
            document.getElementById('itemForm').reset();
            document.getElementById('modalTitle').textContent = 'Novo Item';
            openModal(itemModal);
        });

        // Fechar modal
        btnCancelar?.addEventListener('click', () => closeModal(itemModal));
        closeModalBtn?.addEventListener('click', () => closeModal(itemModal));
        itemModal?.addEventListener('click', function(e) {
            if (e.target === this) closeModal(this);
        });

        function openModal(modalElement) {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            if (currentTheme === 'dark') {
                modalElement.classList.add('dark-mode');
            } else {
                modalElement.classList.remove('dark-mode');
            }
            modalElement.style.display = 'block';
        }
    }

    // Inicializar componentes
    loadPriorityItems();
    setupItemModal();

    // Carregar Chart.js dinamicamente se não estiver disponível
    if (typeof Chart === 'undefined') {
        const script = document.createElement('script');
        script.src = 'https://cdn.jsdelivr.net/npm/chart.js';
        script.onload = initCharts;
        document.head.appendChild(script);
    } else {
        initCharts();
    }
});