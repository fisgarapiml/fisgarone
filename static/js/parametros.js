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

// Carregamento inicial
function fetchCategorias() { fetchList('/api/categorias', 'lista-categorias', renderCategoria);}
function fetchFornecedores() { fetchList('/api/fornecedores', 'lista-fornecedores', renderFornecedor);}
function fetchCentro() { fetchList('/api/centro_de_custo', 'lista-centro', renderCentro);}
function fetchBanco() { fetchList('/api/contas_bancarias', 'lista-banco', renderBanco);}
document.addEventListener('DOMContentLoaded', () => {
    fetchCategorias(); fetchFornecedores(); fetchCentro(); fetchBanco();
    postForm('api/categorias', 'form-categoria', fetchCategorias);
    postForm('api/fornecedores', 'form-fornecedor', fetchFornecedores);
    postForm('api/centro_de_custo', 'form-centro', fetchCentro);
    postForm('api/contas_bancarias', 'form-banco', fetchBanco);
});
