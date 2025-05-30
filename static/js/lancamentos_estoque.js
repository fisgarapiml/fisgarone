document.addEventListener('DOMContentLoaded', function () {
    let tabulatorTable = null;
    let estoqueData = [];

    // DARK MODE
    const body = document.body;
    const toggleDark = document.getElementById('btn-darkmode');
    function setDarkMode(on) {
        if (on) {
            body.classList.add('dark-mode');
            document.querySelectorAll('.offcanvas-panel').forEach(el => el.classList.add('dark-mode'));
            localStorage.setItem('dark-mode', '1');
        } else {
            body.classList.remove('dark-mode');
            document.querySelectorAll('.offcanvas-panel').forEach(el => el.classList.remove('dark-mode'));
            localStorage.setItem('dark-mode', '0');
        }
    }
    // Inicialização dark mode
    setDarkMode(localStorage.getItem('dark-mode') === '1');
    toggleDark.onclick = () => setDarkMode(!body.classList.contains('dark-mode'));

    // Alternância Cards/Grid
    const btnCards = document.getElementById('btn-view-cards');
    const btnGrid = document.getElementById('btn-view-grid');
    const cardsArea = document.getElementById('catalogo-estoque');
    const gridArea = document.getElementById('tabulator-estoque');

    function switchToCards() {
        cardsArea.style.display = 'flex';
        gridArea.style.display = 'none';
        btnCards.classList.add('ativo');
        btnGrid.classList.remove('ativo');
        renderCatalogo();
    }
    function switchToGrid() {
        cardsArea.style.display = 'none';
        gridArea.style.display = 'block';
        btnGrid.classList.add('ativo');
        btnCards.classList.remove('ativo');
        if (!tabulatorTable) criarTabulator(estoqueData);
        else tabulatorTable.replaceData(estoqueData);
    }

    btnCards.onclick = switchToCards;
    btnGrid.onclick = switchToGrid;

    // FILTROS
    const filtroGlobal = document.getElementById('filtro-global');
    const filtroStatus = document.getElementById('filtro-status');
    const filtroFornecedor = document.getElementById('filtro-fornecedor');

    // Fetch data e inicia
    fetch('/estoque/api/lancamentos')
        .then(resp => resp.json())
        .then(data => {
            estoqueData = data;
            switchToCards();
        });

    // Função renderiza catálogo
    function renderCatalogo() {
        // Filtros aplicados ao catálogo
        let filtro = (it) => {
            let termo = filtroGlobal.value?.toLowerCase() || "";
            let status = filtroStatus.value || "";
            let forn = filtroFornecedor.value?.toLowerCase() || "";
            return (!termo || (it.nome?.toLowerCase().includes(termo) || it.sku?.toLowerCase().includes(termo) || it.codigo?.toLowerCase().includes(termo))) &&
                   (!status || it.status === status) &&
                   (!forn || (it.fornecedor_padrao?.toLowerCase().includes(forn)));
        };
        cardsArea.innerHTML = '';
        let filtrados = estoqueData.filter(filtro);
        if (filtrados.length === 0) {
            cardsArea.innerHTML = `<div style="padding: 2vw 4vw; color:#6366f1; font-weight:600; font-size:1.18rem;">Nenhum produto encontrado.</div>`;
            return;
        }
        filtrados.forEach(prod => {
            let img = prod.imagem || '/static/img/noimg.png';
            let statusClass = prod.status === "Inativo" ? "inativo" : "";
            let badges = "";
            if (prod.qtd_estoque < (prod.estoque_minimo || 0)) {
                badges += `<span class="badge-estoque-baixo">Baixo Estoque</span>`;
            }
            cardsArea.innerHTML += `
                <div class="card-produto-estoque" data-id="${prod.id}">
                    <img src="${img}" alt="produto" class="card-produto-img">
                    <div class="card-produto-info">
                        <div class="card-produto-nome">${prod.nome || '(Sem nome)'}</div>
                        <div class="card-produto-badges">${badges}</div>
                        <div>
                            <span class="card-produto-qtd">${prod.qtd_estoque ?? 0} ${prod.unidade ?? ""}</span>
                            <span class="card-produto-status ${statusClass}">${prod.status || ""}</span>
                        </div>
                    </div>
                    <div class="card-produto-actions">
                        <button class="btn-action btn-editar" title="Editar"><i class="bi bi-pencil"></i></button>
                    </div>
                </div>
            `;
        });
        // Ações editar
        document.querySelectorAll('.card-produto-estoque .btn-editar').forEach(btn => {
            btn.onclick = function() {
                let card = btn.closest('.card-produto-estoque');
                let id = card.getAttribute('data-id');
                let prod = estoqueData.find(e => e.id == id);
                abrirPainelEdicao(prod);
            }
        });
    }

    // Atualiza catálogo sempre que filtro mudar
    filtroGlobal.oninput = renderCatalogo;
    filtroStatus.onchange = renderCatalogo;
    filtroFornecedor.onchange = renderCatalogo;

    // Tabulator — grid premium
    function criarTabulator(data) {
        tabulatorTable = new Tabulator("#tabulator-estoque", {
            data: data,
            layout: "fitDataFill",
            reactiveData: true,
            resizableRows: true,
            resizableColumns: true,
            columns: [
                { title: "Imagem", field: "imagem", hozAlign: "center", width: 70, headerSort: false,
                  formatter: (cell) => {
                    let img = cell.getValue();
                    if (!img) img = "/static/img/noimg.png";
                    return `<img src="${img}" alt="produto" style="width:36px;height:36px;border-radius:8px;">`;
                  }
                },
                { title: "SKU", field: "sku", headerFilter: "input", width: 92, editor: false },
                { title: "Código", field: "codigo", headerFilter: "input", width: 92 },
                { title: "Nome", field: "nome", headerFilter: "input", minWidth: 128 },
                { title: "Unid.", field: "unidade", headerFilter: "input", width: 55 },
                { title: "Qtd", field: "qtd_estoque", hozAlign: "center", sorter: "number", width: 72, editor: "number", validator: "integer" },
                { title: "Reserv.", field: "estoque_reservado", hozAlign: "center", width: 65, editor: "number" },
                { title: "Mín.", field: "estoque_minimo", hozAlign: "center", width: 55, editor: "number" },
                { title: "Máx.", field: "estoque_maximo", hozAlign: "center", width: 55, editor: "number" },
                { title: "Loc.", field: "localizacao", width: 62, headerFilter: "input", editor: "input" },
                { title: "Custo", field: "custo_unitario", formatter: "money", formatterParams: { decimal:",", thousand:".", symbol:"R$ ", precision:2 }, hozAlign:"right", width: 90, editor: "number", validator: "numeric" },
                { title: "Venda", field: "preco_venda", formatter: "money", formatterParams: { decimal:",", thousand:".", symbol:"R$ ", precision:2 }, hozAlign:"right", width: 90, editor: "number", validator: "numeric" },
                { title: "Status", field: "status", headerFilter: "select", headerFilterParams: { values: ["", "Ativo", "Inativo"] }, width: 70, editor: "select", editorParams: { values: ["Ativo", "Inativo"] }},
                { title: "Tipo", field: "tipo_produto", width: 72, headerFilter: "select", headerFilterParams: { values:["","Simples","Kit"] }, editor: "select", editorParams: { values: ["Simples", "Kit"] }},
                { title: "Fornecedor", field: "fornecedor_padrao", headerFilter: "input", width: 110, editor: "input" },
                { title: "Cod. Barras", field: "codigo_barras", width: 93, headerFilter: "input", editor: "input" },
                { title: "Cadastro", field: "data_cadastro", width: 98, sorter: "date", headerFilter: "input", editor: false },
                { title: "Atualização", field: "data_atualizacao", width: 98, sorter: "date", headerFilter: "input", editor: false },
                { title: "IPI (%)", field: "percentual_ipi", width: 63, hozAlign: "center", formatter: "money", formatterParams: { decimal:",", thousand:".", symbol:"", precision:2 }, editor: "number" },
                { title: "Custo Tot.", field: "preco_custo_total", width: 96, formatter: "money", formatterParams: { decimal:",", thousand:".", symbol:"R$ ", precision:2 }, hozAlign:"right", editor: "number" },
                {
                  title: "Ações", field: "acoes", headerSort: false, width: 60, hozAlign: "center",
                  formatter: function(cell, formatterParams, onRendered){
                    return `<button class="btn-action btn-editar" title="Editar"><i class="bi bi-pencil"></i></button>`;
                  },
                  cellClick: function(e, cell){
                    const row = cell.getRow().getData();
                    if (e.target.closest('.btn-editar')) { abrirPainelEdicao(row); }
                  }
                }
            ],
            pagination: "local",
            paginationSize: 24,
            paginationSizeSelector: [10, 24, 50, 100, true],
            movableColumns: true,
            clipboard: true,
            height: "auto",
            placeholder: "Nenhum lançamento de estoque encontrado.",
            index: "id",
            selectable: 1,
            rowFormatter: function(row){
                var data = row.getData();
                if (data.qtd_estoque < data.estoque_minimo) { row.getElement().style.background = "#fb718517"; }
                if (data.status && data.status.toLowerCase() === 'inativo') { row.getElement().style.opacity = 0.68; }
            },
        });
        // Exportação
        document.getElementById('btn-export-csv').onclick = function(){ tabulatorTable.download("csv", "estoque.csv"); }
        document.getElementById('btn-export-xlsx').onclick = function(){ tabulatorTable.download("xlsx", "estoque.xlsx", {sheetName:"Estoque"}); }
        document.getElementById('btn-export-pdf').onclick = function(){
            tabulatorTable.download("pdf", "estoque.pdf", {
                orientation:"landscape",
                title:"Lançamentos de Estoque - Grupo Fisgar"
            });
        }
        document.getElementById('btn-print').onclick = function(){ tabulatorTable.print(false, true); }
        document.getElementById('btn-export-backend').onclick = function(){ window.location = "/estoque/lancamentos/exportar"; }

        // Filtros grid
        filtroGlobal.oninput = function(){ tabulatorTable.setFilter([
            {field:"nome", type:"like", value: this.value},
            {field:"sku", type:"like", value: this.value},
            {field:"codigo", type:"like", value: this.value}
        ]); }
        filtroStatus.onchange = function(){ tabulatorTable.setFilter("status", "=", this.value || undefined);}
        filtroFornecedor.onchange = function(){ tabulatorTable.setFilter("fornecedor_padrao", "like", this.value);}
        // Edição inline grid
        tabulatorTable.on("cellEdited", function(cell){
            let data = cell.getRow().getData();
            fetch('/estoque/api/lancamentos/editar', {
                method: "POST",
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({id: data.id, campo: cell.getField(), valor: cell.getValue()})
            })
            .then(r=>r.json())
            .then(res=>{
                if (res.sucesso) {
                    cell.getElement().style.backgroundColor = "#a3e63519";
                    setTimeout(()=>cell.getElement().style.backgroundColor="", 500);
                }
            });
        });
    }

    // Alternância inicial
    btnCards.classList.add('ativo');
    btnGrid.classList.remove('ativo');

    // PAINEL LATERAL EDIÇÃO
    const painelEdicao = document.getElementById('painel-edicao');
    const overlayEdicao = document.getElementById('overlay-edicao');
    const formEditar = document.getElementById('form-editar-estoque');
    function abrirPainelEdicao(prod) {
        for (const [k, v] of Object.entries(prod)) {
            let el = document.getElementById('edit-'+k);
            if(el) el.value = v ?? "";
        }
        painelEdicao.classList.add('aberto');
        overlayEdicao.classList.add('mostrar');
        if (body.classList.contains('dark-mode')) painelEdicao.classList.add('dark-mode');
        else painelEdicao.classList.remove('dark-mode');
    }
    function fecharPainelEdicao() {
        painelEdicao.classList.remove('aberto');
        overlayEdicao.classList.remove('mostrar');
    }
    document.getElementById('btn-close-edicao').onclick = fecharPainelEdicao;
    document.getElementById('btn-cancelar-edicao').onclick = function(e){e.preventDefault(); fecharPainelEdicao();};
    overlayEdicao.onclick = fecharPainelEdicao;

    formEditar.onsubmit = function(ev){
        ev.preventDefault();
        const dados = {};
        Array.from(formEditar.elements).forEach(e=>{
            if(e.name) dados[e.name]=e.value;
        });
        fetch('/estoque/api/lancamentos/editar', {
            method: "POST",
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(dados)
        })
        .then(r=>r.json())
        .then(res=>{
            if(res.sucesso){
                fecharPainelEdicao();
                // Atualiza grid e cards!
                fetch('/estoque/api/lancamentos')
                  .then(resp => resp.json())
                  .then(data => {
                      estoqueData = data;
                      if (cardsArea.style.display === 'flex') renderCatalogo();
                      else if (tabulatorTable) tabulatorTable.replaceData(estoqueData);
                  });
            }
        });
    };
});
