// ==== PAINEL FISGAR NEON (JS AVANÇADO) ==== //
document.addEventListener('DOMContentLoaded', function () {
  let xmls = [];
  let revisados = new Set();
  let modoAtual = "cards";
  let filtroTipo = "";
  let termoBusca = "";

  // Elementos
  const elCards = document.getElementById('fisgar-cards-container');
  const elLista = document.getElementById('fisgar-lista-container');
  const elTabela = document.getElementById('fisgar-tabela-container');
  const elFiltroGlobal = document.getElementById('filtro-global');
  const elFiltroTipo = document.getElementById('filtro-tipo');
  const btnCards = document.getElementById('btn-modo-cards');
  const btnLista = document.getElementById('btn-modo-lista');
  const btnTabela = document.getElementById('btn-modo-tabela');
  const btnProcessar = document.getElementById('btn-processar-massa');

  // ---- Inicializa ----
  fetchXmls();
  alternarModo("cards");
  btnCards.onclick = () => alternarModo("cards");
  btnLista.onclick = () => alternarModo("lista");
  btnTabela.onclick = () => alternarModo("tabela");
  btnProcessar.onclick = () => processarMassa();
  elFiltroGlobal.oninput = () => { termoBusca = elFiltroGlobal.value.toLowerCase(); render(); };
  elFiltroTipo.onchange = () => { filtroTipo = elFiltroTipo.value; render(); };

  // ---- Funções de modo visual ----
  function alternarModo(modo) {
      modoAtual = modo;
      btnCards.classList.toggle("active", modo === "cards");
      btnLista.classList.toggle("active", modo === "lista");
      btnTabela.classList.toggle("active", modo === "tabela");
      elCards.style.display = (modo === "cards") ? "" : "none";
      elLista.style.display = (modo === "lista") ? "" : "none";
      elTabela.style.display = (modo === "tabela") ? "" : "none";
      render();
  }

  // ---- Busca XMLs do backend ----
  function fetchXmls() {
      fetch('/nfe/listar-arquivos')
          .then(r => r.json())
          .then(dados => {
              if (dados.status === "success") {
                  xmls = dados.arquivos || [];
                  revisados = new Set();
                  render();
                  renderCardsTopo();
              }
          });
  }

  function renderCardsTopo() {
      document.getElementById("card-nfe-count").querySelector(".num").textContent = xmls.length;
      let totalValor = 0;
      let totalItens = 0;
      let fornecedores = new Set();
      xmls.forEach(x => {
          if (x.status === "Processado" && x.valor_total) totalValor += parseFloat(x.valor_total);
          if (x.fornecedor) fornecedores.add(x.fornecedor);
          if (x.total_itens) totalItens += parseInt(x.total_itens);
      });
      document.getElementById("card-nfe-total").querySelector(".num").textContent = formatMoeda(totalValor);
      document.getElementById("card-itens-count").querySelector(".num").textContent = totalItens;
      document.getElementById("card-fornecedores").querySelector(".num").textContent = fornecedores.size;
  }

  // ---- Render Principal ----
  function render() {
  let dados = xmls;

  // Filtro por status (processado/não processado/todos)
  if (elFiltroTipo.value === "processados") {
      dados = dados.filter(x => x.status === "Processado");
  } else if (elFiltroTipo.value === "nao-processados") {
      dados = dados.filter(x => x.status === "Não processado");
  }

  // Filtro global (busca por termo em qualquer campo importante)
  if (termoBusca) {
      dados = dados.filter(x =>
          (x.arquivo && x.arquivo.toLowerCase().includes(termoBusca)) ||
          (x.chave && x.chave.toLowerCase().includes(termoBusca)) ||
          (x.fornecedor && x.fornecedor.toLowerCase().includes(termoBusca)) ||
          (x.status && x.status.toLowerCase().includes(termoBusca)) ||
          (x.valor_total && String(x.valor_total).toLowerCase().includes(termoBusca))
      );
  }

  // Filtro por fornecedor ou data, se necessário (personalize conforme seus campos)
  if (elFiltroTipo.value === "fornecedor" && termoBusca) {
      dados = dados.filter(x => x.fornecedor && x.fornecedor.toLowerCase().includes(termoBusca));
  }
  if (elFiltroTipo.value === "data" && termoBusca) {
      dados = dados.filter(x => x.data && x.data.toLowerCase().includes(termoBusca));
  }

  renderCards(dados);
  renderLista(dados);
  renderTabela(dados);
  atualizarBtnProcessar(dados);
}


  // ---- Render Cards ----
  function renderCards(dados) {
  elCards.innerHTML = "";
  dados.forEach((x, idx) => {
      let div = document.createElement('div');
      div.className = "fisgar-xml-card";
      div.innerHTML = `
  <div class="card-fornecedor"><i class="fas fa-building"></i> ${x.fornecedor || "Fornecedor não identificado"}</div>
  <div class="xml-chave"><i class="fas fa-key"></i> ${x.chave || "-"}</div>
  <div class="xml-status ${x.status === 'Processado' ? 'processado' : ''}">${x.status}</div>
  <div class="xml-footer">
      <label><input type="checkbox" class="xml-check" data-idx="${idx}" ${revisados.has(x.arquivo) ? "checked" : ""}> Revisado</label>
      <button class="fisgar-btn fisgar-btn-detalhes" data-arquivo="${x.arquivo}"><i class="fas fa-eye"></i> Detalhes</button>
      <button class="fisgar-btn fisgar-btn-baixar" data-arquivo="${x.arquivo}"><i class="fas fa-download"></i> Baixar</button>
      ${x.status === 'Não processado' ? `<button class="fisgar-btn fisgar-btn-processar" data-arquivo="${x.arquivo}"><i class="fas fa-database"></i> Processar</button>` : ""}
  </div>
`;
      elCards.appendChild(div);
  });
  addEventos();
}

  // ---- Render Lista ----
  function renderLista(dados) {
      elLista.innerHTML = "<ul>" +
          dados.map((x, idx) => `
              <li class="fisgar-xml-lista-item">
                  <span><i class="fas fa-file-alt"></i> ${x.arquivo}<br><span class="xml-chave">${x.chave || "-"}</span></span>
                  <span>
                      <label><input type="checkbox" class="xml-check" data-idx="${idx}" ${revisados.has(x.arquivo) ? "checked" : ""}> Revisado</label>
                      <button class="fisgar-btn fisgar-btn-detalhes" data-arquivo="${x.arquivo}"><i class="fas fa-eye"></i></button>
                      <button class="fisgar-btn fisgar-btn-baixar" data-arquivo="${x.arquivo}"><i class="fas fa-download"></i></button>
                      ${x.status === 'Não processado' ? `<button class="fisgar-btn fisgar-btn-processar" data-arquivo="${x.arquivo}"><i class="fas fa-database"></i></button>` : ""}
                  </span>
              </li>
          `).join('') +
      "</ul>";
      addEventos();
  }

  // ---- Render Tabela ----
  function renderTabela(dados) {
      elTabela.innerHTML = `
          <table>
              <thead>
                  <tr>
                      <th>Revisado</th>
                      <th>Arquivo XML</th>
                      <th>Chave</th>
                      <th>Status</th>
                      <th>Ações</th>
                  </tr>
              </thead>
              <tbody>
                  ${dados.map((x, idx) => `
                      <tr>
                          <td><input type="checkbox" class="xml-check" data-idx="${idx}" ${revisados.has(x.arquivo) ? "checked" : ""}></td>
                          <td>${x.arquivo}</td>
                          <td class="xml-chave">${x.chave || "-"}</td>
                          <td><span class="xml-status ${x.status === 'Processado' ? 'processado' : ''}">${x.status}</span></td>
                          <td>
                              <button class="fisgar-btn fisgar-btn-detalhes" data-arquivo="${x.arquivo}"><i class="fas fa-eye"></i></button>
                              <button class="fisgar-btn fisgar-btn-baixar" data-arquivo="${x.arquivo}"><i class="fas fa-download"></i></button>
                              ${x.status === 'Não processado' ? `<button class="fisgar-btn fisgar-btn-processar" data-arquivo="${x.arquivo}"><i class="fas fa-database"></i></button>` : ""}
                          </td>
                      </tr>
                  `).join('')}
              </tbody>
          </table>
      `;
      addEventos();
  }

  function addEventos() {
      document.querySelectorAll('.fisgar-btn-detalhes').forEach(btn => {
          btn.onclick = () => showModal(btn.dataset.arquivo);
      });
      document.querySelectorAll('.fisgar-btn-baixar').forEach(btn => {
          btn.onclick = () => baixarXml(btn.dataset.arquivo);
      });
      document.querySelectorAll('.fisgar-btn-processar').forEach(btn => {
          btn.onclick = () => processarIndividual(btn.dataset.arquivo);
      });
      document.querySelectorAll('.xml-check').forEach(box => {
          box.onchange = function () {
              let idx = this.getAttribute('data-idx');
              if (this.checked) revisados.add(xmls[idx].arquivo);
              else revisados.delete(xmls[idx].arquivo);
              atualizarBtnProcessar(xmls);
          };
      });
  }

  function atualizarBtnProcessar(dados) {
      let marcados = Array.from(revisados).filter(arq =>
          dados.some(x => x.arquivo === arq && x.status === 'Não processado')
      );
      btnProcessar.disabled = marcados.length === 0;
  }

 // Modal detalhes (Bloco para substituir no seu JS painel_nfe.js)
// Atualize a função showModal
// Modal detalhes - Função showModal corrigida
function showModal(arquivo) {
  // Mostra loader
  const modalBody = document.getElementById('modal-nfe-body');
  modalBody.innerHTML = `
      <div class="loading-modal">
          <i class="fas fa-spinner fa-spin"></i> Carregando dados da NF-e...
      </div>
  `;
  document.getElementById('modal-nfe-bg').style.display = "flex";

  fetch(`/nfe/visualizar-xml?arquivo=${encodeURIComponent(arquivo)}`)
      .then(response => {
          if (!response.ok) {
              throw new Error(`HTTP error! status: ${response.status}`);
          }
          return response.json();
      })
      .then(data => {
          if (data.status !== 'success') {
              throw new Error(data.message || 'Resposta inválida do servidor');
          }

          const nfe = data.dados;
          const produtos = nfe.produtos || [];

          const html = `
              <div class="modal-header">
                  <h3>Detalhes da NF-e</h3>
                  <div class="nfe-info">
                      <p><strong>Chave:</strong> ${nfe.chave || 'Não informada'}</p>
                      <p><strong>Fornecedor:</strong> ${nfe.emitente?.nome || 'Não informado'}</p>
                      <p><strong>CNPJ:</strong> ${nfe.emitente?.cnpj || 'Não informado'}</p>
                      <p><strong>Data Emissão:</strong> ${nfe.data_emissao || 'Não informada'}</p>
                      <p><strong>Valor Total:</strong> ${formatMoeda(nfe.valor_total || 0)}</p>
                  </div>
              </div>
              <div class="produtos-list">
                  <h4>Produtos (${produtos.length})</h4>
                  ${produtos.length > 0 ?
                      produtos.map(prod => `
                          <div class="produto-item">
                              <h5>${prod.descricao || 'Produto sem descrição'}</h5>
                              <div class="produto-detalhes">
                                  <p><strong>Código:</strong> ${prod.codigo || '-'}</p>
                                  <p><strong>NCM:</strong> ${prod.ncm || '-'}</p>
                                  <p><strong>Quantidade:</strong> ${prod.quantidade || 0} ${prod.unidade || 'UN'}</p>
                                  <p><strong>Valor Unitário:</strong> ${formatMoeda(prod.valor_unitario || 0)}</p>
                                  <p><strong>Valor Total:</strong> ${formatMoeda(prod.valor_total || 0)}</p>
                              </div>
                          </div>
                      `).join('') :
                      '<p class="no-produtos">Nenhum produto encontrado</p>'
                  }
              </div>
          `;

          modalBody.innerHTML = html;
          // Sempre adiciona evento de fechar se houver o botão "close-modal-nfe"
const btnFechar = document.getElementById('close-modal-nfe');
if (btnFechar) {
  btnFechar.onclick = function() {
      document.getElementById('modal-nfe-bg').style.display = "none";
  };
}

      })

      .catch(error => {
          console.error('Erro:', error);
          modalBody.innerHTML = `
              <div class="error-message">
                  <i class="fas fa-exclamation-triangle"></i>
                  <h4>Erro ao carregar NF-e</h4>
                  <p>${error.message}</p>
                  <button class="retry-btn" onclick="showModal('${arquivo}')">
                      Tentar novamente
                  </button>
              </div>
          `;
      });
}

// Função baixarXml (mantida igual)
function baixarXml(arquivo) {
  if (!arquivo) {
      alert('Nome do arquivo inválido');
      return;
  }

  const link = document.createElement('a');
  link.href = `/nfe/baixar-xml?arquivo=${encodeURIComponent(arquivo)}`;
  link.target = '_blank';
  link.rel = 'noopener noreferrer';
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// Atualize a função addEventos
function addEventos() {
  document.querySelectorAll('.fisgar-btn-detalhes').forEach(btn => {
      btn.onclick = (e) => {
          e.stopPropagation();
          showModal(btn.dataset.arquivo);
      };
  });

  document.querySelectorAll('.fisgar-btn-baixar').forEach(btn => {
      btn.onclick = (e) => {
          e.stopPropagation();
          baixarXml(btn.dataset.arquivo);
      };
  });

  document.querySelectorAll('.fisgar-btn-processar').forEach(btn => {
      btn.onclick = (e) => {
          e.stopPropagation();
          processarIndividual(btn.dataset.arquivo);
      };
  });

  document.querySelectorAll('.xml-check').forEach(box => {
      box.onchange = function() {
          let idx = this.getAttribute('data-idx');
          if (this.checked) revisados.add(xmls[idx].arquivo);
          else revisados.delete(xmls[idx].arquivo);
          atualizarBtnProcessar(xmls);
      };
  });
}
  // Processar em massa
  function processarMassa() {
      if (revisados.size === 0) return;
      if (!confirm('Processar todas as NF-e marcadas como revisadas?')) return;
      let arquivos = Array.from(revisados);
      function next(i) {
          if (i >= arquivos.length) {
              fetchXmls();
              revisados.clear();
              return;
          }
          fetch('/nfe/salvar-xml', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ arquivo: arquivos[i] })
          })
          .then(() => next(i + 1));
      }
      next(0);
  }
  // Utilitário
  function formatMoeda(valor) {
      return new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' }).format(valor || 0);
  }
});
function processarIndividual(arquivo) {
  alert('Função processarIndividual não implementada! XML: ' + arquivo);
  // Aqui entra a lógica real de chamada AJAX para processar esse XML
}
