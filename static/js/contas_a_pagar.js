// =============================================
// CONSTANTES E VARIÁVEIS GLOBAIS
// =============================================
let currentFilter = 'all';

// =============================================
// FUNÇÕES PRINCIPAIS
// =============================================

/**
 * Renderiza a timeline diária de pagamentos
 */
function renderDailyTimeline() {
  const grid = document.getElementById('daily-grid');
  if (!grid) return;

  grid.innerHTML = '';
  const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();
  const today = new Date();

  for (let day = 1; day <= daysInMonth; day++) {
    const dayStr = day.toString().padStart(2, '0');
    const monthStr = currentMonth.toString().padStart(2, '0');
    const dateKey = `${currentYear}-${monthStr}-${dayStr}`;
    const date = new Date(currentYear, currentMonth - 1, day);
    const dayData = dailyPayments[day] || { total: 0, status: "none" };

    const dayCard = document.createElement('div');
    dayCard.className = `day-card ${dayData.status}`;
    dayCard.dataset.date = dateKey;

    if (day === today.getDate() && currentMonth === today.getMonth() + 1 && currentYear === today.getFullYear()) {
      dayCard.classList.add('current-day');
    }

    dayCard.innerHTML = `
      <div class="day-header">
        <span class="day-name">${date.toLocaleDateString('pt-BR', { weekday: 'short' })}</span>
        <span class="day-date">${dayStr}</span>
      </div>
      <div class="day-total">
        ${dayData.total > 0 ? 'R$ ' + dayData.total.toLocaleString('pt-BR', { minimumFractionDigits: 2 }) : '-'}
      </div>
    `;

    dayCard.addEventListener('click', () => filterByDate(dateKey));
    grid.appendChild(dayCard);
  }
}

/**
 * Mostra transações conforme o filtro selecionado
 * @param {string} filterType - Tipo de filtro (all, paid, balance, today, overdue)
 */
function showTransactions(filterType) {
  currentFilter = filterType;

  // Ativa o card clicado
  document.querySelectorAll('.card').forEach(card => {
    card.classList.remove('active');
  });
  document.querySelector(`.card[data-filter="${filterType}"]`).classList.add('active');

  // Filtra os lançamentos
  const filteredTransactions = filterTransactions(filterType);

  // Atualiza o título
  const titles = {
    'all': 'Todos os Lançamentos',
    'paid': 'Lançamentos Pagos',
    'balance': 'Lançamentos em Aberto',
    'today': 'Lançamentos para Hoje',
    'overdue': 'Lançamentos Atrasados'
  };
  document.getElementById('transactions-title').textContent = titles[filterType];

  // Renderiza a tabela
  renderTransactionsTable(filteredTransactions);

  // Mostra o container
  document.getElementById('transactions-container').style.display = 'block';
}

/**
 * Filtra transações conforme o tipo
 */
function filterTransactions(filterType) {
  const hoje = new Date();
  hoje.setHours(0, 0, 0, 0);

  return lancamentosData.filter(transaction => {
    const [day, month, year] = transaction.vencimento.split('/');
    const vencimento = new Date(year, month - 1, day);

    switch(filterType) {
      case 'all': return true;
      case 'paid': return transaction.pago > 0;
      case 'balance': return transaction.pago <= 0;
      case 'today': return transaction.pago <= 0 && vencimento.toDateString() === hoje.toDateString();
      case 'overdue': return transaction.pago <= 0 && vencimento < hoje;
      default: return true;
    }
  });
}

/**
 * Renderiza a tabela de transações
 */
function renderTransactionsTable(transactions) {
  const container = document.getElementById('transactions-content');

  if (!transactions.length) {
    container.innerHTML = `
      <div class="no-transactions">
        <i class="bi bi-database" style="font-size: 2rem; margin-bottom: 10px;"></i>
        <p>Nenhum lançamento encontrado</p>
      </div>
    `;
    return;
  }

  let html = `
    <table class="transactions-table">
      <thead>
        <tr>
          <th>Fornecedor</th>
          <th>Categoria</th>
          <th>Plano</th>
          <th>Vencimento</th>
          <th>Valor</th>
          <th>Status</th>
          <th>Ações</th>
        </tr>
      </thead>
      <tbody>
  `;

  transactions.forEach(trans => {
    const [day, month, year] = trans.vencimento.split('/');
    const venc = new Date(year, month - 1, day);
    const hoje = new Date();
    hoje.setHours(0, 0, 0, 0);
    const status = trans.pago > 0 ? 'paid' : venc < hoje ? 'overdue' : 'pending';
    const label = status === 'paid' ? 'Pago' : status === 'pending' ? 'Aberto' : 'Atrasado';

    html += `
      <tr>
        <td>${trans.fornecedor || '-'}</td>
        <td>${trans.categoria || '-'}</td>
        <td>${trans.plano || '-'}</td>
        <td>${trans.vencimento}</td>
        <td>${formatar_brl(trans.valor)}</td>
        <td><span class="transaction-status status-${status}">${label}</span></td>
        <td>
          <div class="transaction-actions">
            <button class="action-btn" title="Editar" onclick="editTransaction(${trans.codigo})">
              <i class="bi bi-pencil"></i>
            </button>
            ${trans.pago <= 0 ? `
            <button class="action-btn complete" title="Dar Baixa" onclick="markAsPaid(${trans.codigo})">
              <i class="bi bi-check-lg"></i>
            </button>
            ` : ''}
            <button class="action-btn delete" title="Excluir" onclick="deleteTransaction(${trans.codigo})">
              <i class="bi bi-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `;
  });

  html += '</tbody></table>';
  container.innerHTML = html;
}

// =============================================
// FUNÇÕES DE INTERAÇÃO
// =============================================

function hideTransactions() {
  document.getElementById('transactions-container').style.display = 'none';
  document.querySelectorAll('.card').forEach(card => {
    card.classList.remove('active');
  });
}

function editTransaction(codigo) {
  const transaction = lancamentosData.find(t => t.codigo == codigo);
  if (!transaction) return;

  document.getElementById('edit-codigo').value = transaction.codigo;
  document.getElementById('edit-fornecedor').value = transaction.fornecedor || '';
  document.getElementById('edit-categoria').value = transaction.categoria || '';
  document.getElementById('edit-plano').value = transaction.plano || '';

  // Formata data DD/MM/YYYY para YYYY-MM-DD
  const [day, month, year] = transaction.vencimento.split('/');
  document.getElementById('edit-vencimento').value = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;

  document.getElementById('edit-valor').value = transaction.valor;
  document.getElementById('edit-pago').value = transaction.pago > 0 ? '1' : '0';
  document.getElementById('edit-modal').style.display = 'flex';
}

function closeEditModal() {
  document.getElementById('edit-modal').style.display = 'none';
}

function saveTransaction() {
  const codigo = document.getElementById('edit-codigo').value;
  const fornecedor = document.getElementById('edit-fornecedor').value;
  const categoria = document.getElementById('edit-categoria').value;
  const plano = document.getElementById('edit-plano').value;
  const venc = document.getElementById('edit-vencimento').value;
  const valor = document.getElementById('edit-valor').value;
  const pago = document.getElementById('edit-pago').value;

  // Formata data de YYYY-MM-DD para DD/MM/YYYY
  const [year, month, day] = venc.split('-');
  const formattedDate = `${day}/${month}/${year}`;

  fetch('/contas-a-pagar/editar_lancamento', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      codigo: codigo,
      fornecedor: fornecedor,
      categorias: categoria,
      plano_de_contas: plano,
      vencimento: formattedDate,
      valor: valor,
      valor_pago: pago
    })
  })
  .then(response => {
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    return response.json();
  })
  .then(data => {
    if (data.success) {
      alert('Lançamento atualizado com sucesso!');
      closeEditModal();
      location.reload();
    } else {
      alert('Erro ao atualizar: ' + data.error);
    }
  })
  .catch(err => {
    console.error(err);
    alert('Falha na comunicação com o servidor.');
  });
}

function markAsPaid(codigo) {
  if (confirm('Deseja marcar este lançamento como pago?')) {
    fetch(`/marcar_pago?codigo=${codigo}`, { method: 'POST' })
      .then(res => {
        if (res.ok) {
          alert('Lançamento marcado como pago.');
          location.reload();
        } else {
          alert('Erro ao marcar como pago.');
        }
      });
  }
}

function deleteTransaction(codigo) {
  if (confirm('Tem certeza que deseja excluir este lançamento?')) {
    fetch(`/excluir?codigo=${codigo}`, { method: 'POST' })
      .then(res => {
        if (res.ok) {
          alert('Lançamento excluído com sucesso.');
          location.reload();
        } else {
          alert('Erro ao excluir o lançamento.');
        }
      });
  }
}

// =============================================
// FUNÇÕES DE NAVEGAÇÃO
// =============================================

function changeMonth(offset) {
  currentMonth += offset;

  if (currentMonth > 12) {
    currentMonth = 1;
    currentYear++;
  } else if (currentMonth < 1) {
    currentMonth = 12;
    currentYear--;
  }

  window.location.href = `/contas-a-pagar?mes=${currentMonth}&ano=${currentYear}`;
}

function filterByDate(date = null) {
  if (!date) {
    const dateInput = document.getElementById('filter-date');
    date = dateInput.value;
  }

  if (date) {
    const [year, month, day] = date.split('-');
    window.location.href = `/contas-a-pagar?mes=${month}&ano=${year}${day ? '&dia=' + day : ''}`;
  }
}

// =============================================
// FUNÇÕES DE GRÁFICOS
// =============================================

let chartBarras = null;
let chartPizza = null;

function carregarGraficoEvolucao(filtro = 'ano') {
  fetch('/contas-a-pagar/api/contas_por_mes')
    .then(response => response.json())
    .then(data => {
      let dadosFiltrados = filtro === 'ano' ?
        data.filter(item => item.mes.endsWith('/' + currentYear)) :
        data;

      const labels = dadosFiltrados.map(item => item.mes);
      const previsto = dadosFiltrados.map(item => item.previsto);
      const pago = dadosFiltrados.map(item => item.pago);

      if (chartBarras) chartBarras.destroy();

      const ctx = document.getElementById('graficoContasMensais').getContext('2d');
      chartBarras = new Chart(ctx, {
        type: 'bar',
        data: {
          labels: labels,
          datasets: [
            {
              label: 'Previsto',
              data: previsto,
              backgroundColor: 'rgba(0, 102, 255, 0.2)',
              borderColor: '#0066ff',
              borderWidth: 2,
              borderRadius: 10
            },
            {
              label: 'Pago',
              data: pago,
              backgroundColor: 'rgba(0, 200, 83, 0.2)',
              borderColor: '#00c853',
              borderWidth: 2,
              borderRadius: 10
            }
          ]
        },
        options: {
          responsive: true,
          onClick: (evt, elements) => {
            if (elements.length > 0) {
              const mesSelecionado = chartBarras.data.labels[elements[0].index];
              mostrarLancamentosFiltrados({ tipo: 'mes', valor: mesSelecionado });
            }
          }
        }
      });
    });
}

function carregarGraficoCategorias(filtro = 'mes') {
  let url = '/contas-a-pagar/api/categorias_agrupadas';
  if (filtro === 'mes') url += `?mes=${currentMonth}&ano=${currentYear}`;
  if (filtro === 'ano') url += `?ano=${currentYear}`;

  fetch(url)
    .then(response => response.json())
    .then(data => {
      if (chartPizza) chartPizza.destroy();

      chartPizza = new Chart(document.getElementById('graficoCategorias'), {
        type: 'doughnut',
        data: {
          labels: data.map(item => item.categoria),
          datasets: [{
            data: data.map(item => item.total),
            backgroundColor: [
              '#0066ff', '#00c853', '#ffab00', '#ff3d00',
              '#6200ea', '#00bcd4', '#607d8b', '#8bc34a'
            ]
          }]
        },
        options: {
          onClick: (evt, elements) => {
            if (elements.length > 0) {
              const categoria = chartPizza.data.labels[elements[0].index];
              mostrarLancamentosFiltrados({ tipo: 'categoria', valor: categoria });
            }
          }
        }
      });
    });
}

// =============================================
// FUNÇÕES AUXILIARES
// =============================================

function mostrarLancamentosFiltrados(filtro) {
  let url = `/contas-a-pagar/api/lancamentos_filtrados?tipo=${filtro.tipo}&valor=${encodeURIComponent(filtro.valor)}`;

  if (filtro.tipo === 'categoria') {
    url += `&mes=${currentMonth}&ano=${currentYear}`;
  }

  fetch(url)
    .then(res => res.json())
    .then(transactions => {
      const modalTitle = document.getElementById('modal-title');
      const modalBody = document.getElementById('modal-body');

      modalTitle.textContent = `Lançamentos - ${filtro.valor}`;

      if (!transactions.length) {
        modalBody.innerHTML = '<p style="text-align:center;color:#777;">Nenhum lançamento encontrado.</p>';
      } else {
        modalBody.innerHTML = `
          <table style="width:100%;">
            <thead>
              <tr>
                <th>Fornecedor</th>
                <th>Vencimento</th>
                <th>Valor</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              ${transactions.map(trans => `
                <tr>
                  <td>${trans.fornecedor}</td>
                  <td>${trans.vencimento}</td>
                  <td>${formatar_brl(trans.valor)}</td>
                  <td>${trans.pago > 0 ? 'Pago' : 'Pendente'}</td>
                </tr>
              `).join('')}
            </tbody>
          </table>
        `;
      }

      document.getElementById('modal-lancamentos').style.display = 'flex';
    });
}

function fecharModal() {
  document.getElementById('modal-lancamentos').style.display = 'none';
}

function formatar_brl(valor) {
  return 'R$ ' + parseFloat(valor).toFixed(2).replace('.', ',');
}

// =============================================
// INICIALIZAÇÃO
// =============================================

document.addEventListener('DOMContentLoaded', () => {
  renderDailyTimeline();

  // Event listeners
  document.getElementById('filtro-evolucao').addEventListener('change', e => {
    carregarGraficoEvolucao(e.target.value);
  });

  document.getElementById('filtro-categoria').addEventListener('change', e => {
    carregarGraficoCategorias(e.target.value);
  });

  document.getElementById('btn-exportar-pdf').addEventListener('click', () => {
    const filtro = document.getElementById('modal-title').textContent;
    window.open(`/contas-a-pagar/pdf?filtro=${encodeURIComponent(filtro)}`, '_blank');
  });

  // Inicializa gráficos
  carregarGraficoEvolucao();
  carregarGraficoCategorias();
});

// =============================================
// FUNÇÕES DE PDF
// =============================================

function togglePDFOptions() {
  const options = document.getElementById('pdfOptions');
  options.style.display = options.style.display === 'block' ? 'none' : 'block';
}

function gerarPDF(filtro) {
  document.getElementById('pdfOptions').style.display = 'none';
  window.open(`/contas-a-pagar/pdf?filtro=${filtro}&mes=${currentMonth}&ano=${currentYear}`, '_blank');
}

// Fecha o menu PDF ao clicar fora
document.addEventListener('click', (event) => {
  const pdfOptions = document.getElementById('pdfOptions');
  const pdfButton = document.querySelector('.pdf-main-button');

  if (!pdfOptions.contains(event.target) && event.target !== pdfButton) {
    pdfOptions.style.display = 'none';
  }
});