// --- Funções AJAX Genéricas ---
function fetchList(api, tbodyId, render) {
    fetch(api)
        .then(r => r.json())
        .then(lista => {
            const el = document.getElementById(tbodyId);
            el.innerHTML = '';
            lista.forEach(dado => el.innerHTML += render(dado));
        });
}

function postForm(api, formId, callback) {
    const form = document.getElementById(formId);
    form.onsubmit = e => {
        e.preventDefault();
        const data = Object.fromEntries(new FormData(form));
        fetch(api, {method: 'POST', headers: {'Content-Type':'application/json'}, body: JSON.stringify(data)})
            .then(() => { form.reset(); callback(); });
    }
}

function deleteItem(api, id, callback) {
    fetch(api + '?id=' + id, {method: 'DELETE'})
        .then(() => callback());
}

function renderCategoria(d) {
    return `<tr>
        <td>${d.nome}</td><td>${d.descricao||''}</td>
        <td>
            <button class="btn btn-danger btn-sm" onclick="deleteItem('/api/categorias', ${d.id}, () => fetchCategorias())"><i class="ri-delete-bin-6-line"></i></button>
        </td>
    </tr>`;
}
function renderFornecedor(d) {
    return `<tr>
        <td>${d.nome}</td><td>${d.cnpj||''}</td><td>${d.email||''}</td><td>${d.telefone||''}</td>
        <td>
            <button class="btn btn-danger btn-sm" onclick="deleteItem('/api/fornecedores', ${d.id}, () => fetchFornecedores())"><i class="ri-delete-bin-6-line"></i></button>
        </td>
    </tr>`;
}
function renderCentro(d) {
    return `<tr>
        <td>${d.nome}</td><td>${d.descricao||''}</td>
        <td>
            <button class="btn btn-danger btn-sm" onclick="deleteItem('/api/centro_de_custo', ${d.id}, () => fetchCentro())"><i class="ri-delete-bin-6-line"></i></button>
        </td>
    </tr>`;
}
function renderBanco(d) {
    return `<tr>
        <td>${d.banco}</td><td>${d.agencia||''}</td><td>${d.conta||''}</td><td>${d.titular||''}</td><td>${d.tipo_conta||''}</td>
        <td>
            <button class="btn btn-danger btn-sm" onclick="deleteItem('/api/contas_bancarias', ${d.id}, () => fetchBanco())"><i class="ri-delete-bin-6-line"></i></button>
        </td>
    </tr>`;
}
let sugestoesSelecionadas = [];
let campoAtualSugestao = '';

function abrirSugestoes(campo) {
    campoAtualSugestao = campo;
    fetch(`/api/sugestoes/${campo}`)
        .then(r => r.json())
        .then(lista => {
            sugestoesSelecionadas = []; // reseta
            let html = '<table class="table table-dark table-hover">';
            html += '<thead><tr><th></th><th>Nome</th><th>Editar</th></tr></thead><tbody>';
            lista.forEach((nome, idx) => {
                html += `
                  <tr>
                    <td><input type="checkbox" onchange="marcarSugestao(${idx}, this.checked)"></td>
                    <td><input type="text" class="form-control form-control-sm" id="sugestao-${idx}" value="${nome.replace(/"/g, '&quot;')}"></td>
                    <td></td>
                  </tr>
                `;
            });
            html += '</tbody></table>';
            document.getElementById('lista-sugestoes').innerHTML = html;
            // limpa seleção
            sugestoesSelecionadas = new Array(lista.length).fill(false);
            let modal = new bootstrap.Modal(document.getElementById('modal-sugestoes'));
            modal.show();
        });
}

function marcarSugestao(idx, marcado) {
    sugestoesSelecionadas[idx] = marcado;
}

function salvarSugestoes() {
    const inputs = document.querySelectorAll('#lista-sugestoes input[type="text"]');
    let selecionados = [];
    inputs.forEach((inp, idx) => {
        if (sugestoesSelecionadas[idx]) {
            selecionados.push(inp.value.trim());
        }
    });
    if (!selecionados.length) return alert("Selecione pelo menos um!");
    // Monta dados conforme o campo
    let rota = '', bodyList = [];
    if (campoAtualSugestao === 'fornecedor') {
        rota = '/api/fornecedores';
        bodyList = selecionados.map(nome => ({ nome }));
    }
    if (campoAtualSugestao === 'categorias') {
        rota = '/api/categorias';
        bodyList = selecionados.map(nome => ({ nome }));
    }
    if (campoAtualSugestao === 'centro_de_custo') {
        rota = '/api/centro_de_custo';
        bodyList = selecionados.map(nome => ({ nome }));
    }
    if (campoAtualSugestao === 'banco_pagamento') {
        rota = '/api/contas_bancarias';
        bodyList = selecionados.map(banco => ({ banco }));
    }
    // Faz vários POSTs em sequência
    Promise.all(
        bodyList.map(dado =>
            fetch(rota, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(dado)})
        )
    ).then(() => {
        alert('Itens salvos!');
        document.querySelector('.modal.show [data-bs-dismiss="modal"]').click();
        // Atualiza a listagem
        if (rota === '/api/fornecedores') fetchFornecedores();
        if (rota === '/api/categorias') fetchCategorias();
        if (rota === '/api/centro_de_custo') fetchCentro();
        if (rota === '/api/contas_bancarias') fetchBanco();
    });
}


// Carregamento inicial
function fetchCategorias() { fetchList('/api/categorias', 'lista-categorias', renderCategoria);}
function fetchFornecedores() { fetchList('/api/fornecedores', 'lista-fornecedores', renderFornecedor);}
function fetchCentro() { fetchList('/api/centro_de_custo', 'lista-centro', renderCentro);}
function fetchBanco() { fetchList('/api/contas_bancarias', 'lista-banco', renderBanco);}
document.addEventListener('DOMContentLoaded', () => {
    fetchCategorias(); fetchFornecedores(); fetchCentro(); fetchBanco();
    postForm('/api/categorias', 'form-categoria', fetchCategorias);
    postForm('/api/fornecedores', 'form-fornecedor', fetchFornecedores);
    postForm('/api/centro_de_custo', 'form-centro', fetchCentro);
    postForm('/api/contas_bancarias', 'form-banco', fetchBanco);

});
