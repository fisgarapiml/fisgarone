// Variável global para edição
let produtoEditando = null;

document.addEventListener('DOMContentLoaded', function() {
    // 1. Configuração das Tabs
    const tabs = document.querySelectorAll('.tab[data-tab]');
    tabs.forEach(tab => {
        tab.addEventListener('click', function() {
            // Remove classe ativa de todas as tabs
            tabs.forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.panel').forEach(p => p.classList.remove('active'));

            // Ativa tab clicada
            this.classList.add('active');
            const tabId = this.getAttribute('data-tab');
            document.getElementById(`panel-${tabId}`).classList.add('active');

            // Carrega dinamicamente se for 'todos'
            if (tabId === 'todos') {
                carregarTodos();
            }
        });
    });

    // 2. Botão de atualizar
    document.getElementById('btn-atualizar').addEventListener('click', function() {
        window.location.reload();
    });

    // 3. Configuração do Modal
    window.editarConfiguracao = editarConfiguracao;
    window.fecharModal = fecharModal;
    window.salvarEdicao = salvarEdicao;
    window.salvarConfiguracao = salvarConfiguracao;
});

// Função para salvar nova configuração
async function salvarConfiguracao(codigo, nome, unidade, volume, pacote) {
    if (!volume || !pacote) {
        alert('Por favor, preencha todos os campos');
        return;
    }

    try {
        const response = await fetch('/config-unidades/api/salvar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                codigo_fornecedor: codigo,
                nome: nome,
                unidade_compra: unidade,
                qtd_por_volume: volume,
                qtd_por_pacote: pacote
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            alert('Configuração salva com sucesso!');
            window.location.reload();
        } else {
            alert('Erro: ' + (data.message || 'Falha ao salvar'));
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('Erro ao conectar com o servidor');
    }
}

// Função para abrir modal de edição
function editarConfiguracao(codigo, nome, unidade, volume, pacote) {
    produtoEditando = { codigo, nome, unidade, volume, pacote };

    document.getElementById('modal-nome').value = nome;
    document.getElementById('modal-codigo').value = codigo;
    document.getElementById('modal-unidade').value = unidade;
    document.getElementById('modal-volume').value = volume;
    document.getElementById('modal-pacote').value = pacote;

    document.getElementById('modal-edicao').style.display = 'flex';
}

// Função para fechar modal
function fecharModal() {
    document.getElementById('modal-edicao').style.display = 'none';
    produtoEditando = null;
}

// Função para salvar edição
async function salvarEdicao() {
    const novoVolume = document.getElementById('modal-volume').value;
    const novoPacote = document.getElementById('modal-pacote').value;

    if (!novoVolume || !novoPacote) {
        alert('Por favor, preencha todos os campos');
        return;
    }

    try {
        const response = await fetch('/config-unidades/api/salvar', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                codigo_fornecedor: produtoEditando.codigo,
                nome: produtoEditando.nome,
                unidade_compra: produtoEditando.unidade,
                qtd_por_volume: novoVolume,
                qtd_por_pacote: novoPacote
            })
        });

        const data = await response.json();

        if (data.status === 'success') {
            alert('Configuração atualizada com sucesso!');
            window.location.reload();
        } else {
            alert('Erro: ' + (data.message || 'Falha ao atualizar'));
        }
    } catch (error) {
        console.error('Erro:', error);
        alert('Erro ao conectar com o servidor');
    }
}

// Função para carregar todos os itens
async function carregarTodos() {
    try {
        const [pendentes, configurados] = await Promise.all([
            fetch('/config-unidades/api/pendentes').then(res => res.json()),
            fetch('/config-unidades/api/configurados').then(res => res.json())
        ]);

        const todos = [...pendentes, ...configurados];
        const container = document.getElementById('lista-todos');
        container.innerHTML = '';

        todos.forEach(item => {
            const card = document.createElement('div');
            card.className = 'product-card';

            const isConfigurado = 'qtd_por_volume' in item;

            card.innerHTML = `
                <div class="product-header">
                    <h3 class="product-title">
                        <i class="fas ${isConfigurado ? 'fa-check-circle' : 'fa-exclamation-circle'}"
                           style="color: ${isConfigurado ? 'var(--success)' : 'var(--warning)'};"></i>
                        ${item.nome}
                        <span class="product-badge">${item.unidade_compra}</span>
                    </h3>
                </div>
                <p class="product-code">Código: ${item.codigo_fornecedor}</p>
                ${isConfigurado ? `
                    <div class="product-meta">
                        <div class="meta-item">
                            <i class="fas fa-box-open"></i>
                            <span>Volume: <span class="meta-value">${item.qtd_por_volume} ${item.unidade_compra}</span></span>
                        </div>
                        <div class="meta-item">
                            <i class="fas fa-boxes"></i>
                            <span>Pacote: <span class="meta-value">${item.qtd_por_pacote} ${item.unidade_compra}</span></span>
                        </div>
                    </div>
                    <div class="form-actions">
                        <button class="btn btn-secondary" onclick="editarConfiguracao(
                            '${item.codigo_fornecedor}',
                            '${item.nome}',
                            '${item.unidade_compra}',
                            '${item.qtd_por_volume}',
                            '${item.qtd_por_pacote}'
                        )">
                            <i class="fas fa-edit"></i> Editar
                        </button>
                    </div>
                ` : `
                    <div class="form-group">
                        <label class="form-label">Quantidade por Volume</label>
                        <input type="number" class="form-input" id="volume-todos-${item.codigo_fornecedor}" placeholder="Ex: 10">
                    </div>
                    <div class="form-group">
                        <label class="form-label">Quantidade por Pacote</label>
                        <input type="number" class="form-input" id="pacote-todos-${item.codigo_fornecedor}" placeholder="Ex: 50">
                    </div>
                    <div class="form-actions">
                        <button class="btn btn-primary" onclick="salvarConfiguracao(
                            '${item.codigo_fornecedor}',
                            '${item.nome}',
                            '${item.unidade_compra}',
                            document.getElementById('volume-todos-${item.codigo_fornecedor}').value,
                            document.getElementById('pacote-todos-${item.codigo_fornecedor}').value
                        )">
                            <i class="fas fa-save"></i> Salvar
                        </button>
                    </div>
                `}
            `;

            container.appendChild(card);
        });

    } catch (error) {
        console.error('Erro ao carregar todos os itens:', error);
        alert('Erro ao carregar dados');
    }
}