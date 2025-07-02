


// Variáveis globais vindas do HTML
const mes = currentMonth;
const ano = currentYear;
const mesAtual = currentMonth;
const anoAtual = currentYear;
const anoAtualEvolucao = currentYear;

function gerarPDFDosLancamentos() {
        try {
            const modalTitle = document.getElementById('modal-title').textContent;
            let filtro = 'all';

            // Mapeia o título do modal para os filtros correspondentes
            if (modalTitle.includes("Atrasados")) filtro = "overdue";
            else if (modalTitle.includes("Pago")) filtro = "paid";
            else if (modalTitle.includes("Hoje")) filtro = "today";
            else if (modalTitle.includes("Previsto")) filtro = "all";
            else if (modalTitle.includes("Saldo")) filtro = "balance";

            // Adiciona parâmetros de mês/ano
            const mes = currentMonth;
            window.open(`/contas-a-pagar/pdf?filtro=${filtro}&mes=${mes}&ano=${ano}`, '_blank');

        } catch (error) {
            console.error("Erro ao gerar PDF:", error);
            alert("Ocorreu um erro ao gerar o PDF");
        }
    }

    // Função para gerar PDF de um lançamento específico (modal de edição)
    function gerarPdfDoLancamento() {
        const codigo = document.getElementById('edit-codigo').value;
        if (!codigo) {
            alert('Nenhum lançamento selecionado!');
            return;
        }
        window.open('/contas-a-pagar/pdf/' + codigo, '_blank');
    }
        function togglePdfOptions() {
  const options = document.getElementById("pdf-options");
  options.style.display = options.style.display === "block" ? "none" : "block";
}

function gerarPDF() {
  const checkboxes = document.querySelectorAll("#pdf-options input[type='checkbox']");
  const selecionados = [];
  checkboxes.forEach(cb => {
    if (cb.checked) selecionados.push(cb.value);
  });

  if (selecionados.length === 0) {
    alert("Selecione pelo menos uma opção para gerar o PDF.");
    return;
  }

  const params = selecionados.map(v => `tipo=${v}`).join("&");
  window.open(`/contas-a-pagar/pdf?${params}`, "_blank");
}

        // Renderiza a timeline diária
        function renderDailyTimeline() {
            const grid = document.getElementById('daily-grid');
            grid.innerHTML = '';

            const daysInMonth = new Date(currentYear, currentMonth, 0).getDate();
            const today = new Date();

            for (let day = 1; day <= daysInMonth; day++) {
                const dayStr = String(day).padStart(2, '0');
                const monthStr = String(currentMonth).padStart(2, '0');
                const dateKey = `${currentYear}-${monthStr}-${dayStr}`;
                const date = new Date(currentYear, currentMonth - 1, day);
                const dayData = dailyPayments[dayStr] || { total: 0, status: "none" };

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

        // Mostra os lançamentos conforme o filtro
        function showTransactions(filterType) {
            currentFilter = filterType;
            document.querySelectorAll('.card').forEach(card => {
  card.addEventListener('click', () => {
    const filtro = card.dataset.filter;
    const titulo = card.querySelector('.card-title').textContent;

    mostrarLancamentosFiltrados({
      tipo: 'card',
      valor: filtro,
      titulo: titulo  // Adiciona o título explicitamente
    });
  });
});

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

        // Filtra os lançamentos
        function filterTransactions(filterType) {
            const hoje = new Date();
            hoje.setHours(0, 0, 0, 0);

            return lancamentosData.filter(transaction => {
                const vencimento = new Date(
                    transaction.vencimento.split('/')[2],
                    transaction.vencimento.split('/')[1] - 1,
                    transaction.vencimento.split('/')[0]
                );

                switch(filterType) {
                    case 'all':
                        return true;
                    case 'paid':
                        return transaction.pago > 0;
                    case 'balance':
                        return transaction.pago <= 0;
                    case 'today':
                        return transaction.pago <= 0 && vencimento.toDateString() === hoje.toDateString();
                    case 'overdue':
                        return transaction.pago <= 0 && vencimento < hoje;
                    default:
                        return true;
                }
            });
        }

        // Renderiza a tabela de lançamentos
        function renderTransactionsTable(transactions) {
            const container = document.getElementById('transactions-content');

            if (transactions.length === 0) {
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
                html += `
                    <tr>
                        <td>${trans.fornecedor || '-'}</td>
                        <td>${trans.categoria || '-'}</td>
                        <td>${trans.plano || '-'}</td>
                        <td>${trans.vencimento}</td>
                        <td>${formatar_brl(trans.valor)}</td>
                        <td>
                            ${(() => {
                                const venc = new Date(trans.vencimento.split('/').reverse().join('-'));
                                const hoje = new Date();
                                hoje.setHours(0, 0, 0, 0);
                                const status = trans.pago > 0 ? 'paid' : venc < hoje ? 'overdue' : 'pending';
                                const label = status === 'paid' ? 'Pago' : status === 'pending' ? 'Aberto' : 'Atrasado';
                                return `<span class="transaction-status status-${status}">${label}</span>`;
                            })()}
                        </td>
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

            html += `</tbody></table>`;
            container.innerHTML = html;
        }

        // Oculta a lista de lançamentos
        function hideTransactions() {
            document.getElementById('transactions-container').style.display = 'none';
            document.querySelectorAll('.card').forEach(card => {
                card.classList.remove('active');
            });
        }

        // Funções de ação
        function editTransaction(codigo) {
            const transaction = lancamentosData.find(t => t.codigo == codigo);
            if (!transaction) return;

            // Preenche o formulário de edição
            document.getElementById('edit-codigo').value = transaction.codigo;
            document.getElementById('edit-fornecedor').value = transaction.fornecedor || '';
            document.getElementById('edit-categoria').value = transaction.categoria || '';
            document.getElementById('edit-plano').value = transaction.plano || '';

            // Formata a data para o formato YYYY-MM-DD
            const [day, month, year] = transaction.vencimento.split('/');
            document.getElementById('edit-vencimento').value = `${year}-${month.padStart(2, '0')}-${day.padStart(2, '0')}`;

            document.getElementById('edit-valor').value = transaction.valor;
            document.getElementById('edit-pago').value = transaction.pago > 0 ? '1' : '0';

            // Mostra o modal
            document.getElementById('edit-modal').style.display = 'flex';
        }

        function closeEditModal() {
            document.getElementById('edit-modal').style.display = 'none';
        }

        function saveTransaction() {
  // 1) Coleta os campos do modal
  const codigo     = document.getElementById('edit-codigo').value;
  const fornecedor = document.getElementById('edit-fornecedor').value;
  const categoria  = document.getElementById('edit-categoria').value;
  const plano      = document.getElementById('edit-plano').value;
  const venc       = document.getElementById('edit-vencimento').value;
  const valor      = document.getElementById('edit-valor').value;
  const pago       = document.getElementById('edit-pago').value;

  // 2) Formata a data de YYYY-MM-DD para DD/MM/YYYY
  const [year, month, day] = venc.split('-');
  const formattedDate = `${day}/${month}/${year}`;

  // 3) Dispara o POST para /contas-a-pagar/editar_lancamento
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
      // Se quiser recarregar a lista via AJAX, chame a função que atualiza a tabela.
      // Aqui, para simplificar, você pode usar:
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

        // Função para formatar valores (simulando a função do Jinja2)
        function formatar_brl(valor) {
            return 'R$ ' + parseFloat(valor).toFixed(2).replace('.', ',');
        }

        // Navegação entre meses
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

        // Filtro por data
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

        // Inicialização
        document.addEventListener('DOMContentLoaded', () => {
            renderDailyTimeline();

            // Se houver um dia específico na URL, mostra os lançamentos
            const urlParams = new URLSearchParams(window.location.search);
            if (urlParams.has('dia')) {
                showTransactions('all');
            }
        });
        function togglePDFOptions() {
    const options = document.getElementById('pdfOptions');
    options.style.display = options.style.display === 'block' ? 'none' : 'block';
}

function gerarPDF(filtro) {
    const mes = new Date().getMonth() + 1;
    const ano = new Date().getFullYear();

    // Fecha o menu de opções
    document.getElementById('pdfOptions').style.display = 'none';

    // Abre o PDF em nova aba
    window.open(`/contas-a-pagar/pdf?filtro=${filtro}&mes=${mes}&ano=${ano}`, '_blank');
}

// Fecha o menu se clicar fora
document.addEventListener('click', function(event) {
    const options = document.getElementById('pdfOptions');
    const button = document.querySelector('.pdf-main-button');

    if (!options.contains(event.target) && event.target !== button) {
        options.style.display = 'none';
    }
});
        let chartBarras = null;


function carregarGraficoEvolucao(filtro = 'ano') {
  fetch('/contas-a-pagar/api/contas_por_mes')
    .then(response => response.json())
    .then(data => {
      let dadosFiltrados = [];

      if (filtro === 'ano') {
        dadosFiltrados = data.filter(item => item.mes && item.mes.endsWith('/' + anoAtualEvolucao));
      } else {
        dadosFiltrados = data; // Todos os meses
      }

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
              borderRadius: 10,
              barPercentage: 0.5,
              categoryPercentage: 0.6
            },
            {
              label: 'Pago',
              data: pago,
              backgroundColor: 'rgba(0, 200, 83, 0.2)',
              borderColor: '#00c853',
              borderWidth: 2,
              borderRadius: 10,
              barPercentage: 0.5,
              categoryPercentage: 0.6
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: {
              ticks: { font: { size: 12 } },
              grid: { display: false }
            },
            y: {
              beginAtZero: true,
              ticks: {
                callback: valor => 'R$ ' + valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 }),
                font: { size: 12 }
              },
              grid: { color: '#f0f0f0' }
            }
          },
          plugins: {
            legend: { labels: { font: { size: 13 } } },
            tooltip: {
              callbacks: {
                label: context => {
                  const valor = context.parsed.y || 0;
                  return `${context.dataset.label}: R$ ${valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
                }
              }
            }
          },
          onClick: (evt, elements) => {
  if (elements.length > 0) {
    const index = elements[0].index;
    const mesSelecionado = chartBarras.data.labels[index];
    mostrarLancamentosFiltrados({ tipo: 'mes', valor: mesSelecionado });
  }
}
        }
      });
    });
}

// Inicializa gráfico
carregarGraficoEvolucao();

// Listener do dropdown
document.getElementById('filtro-evolucao').addEventListener('change', e => {
  carregarGraficoEvolucao(e.target.value);
});


// Use as variáveis globais já definidas no HTML


let chartPizza = null;

function carregarGraficoCategorias(filtro = 'mes') {
  let url = '/contas-a-pagar/api/categorias_agrupadas';

  if (filtro === 'mes') {
    url += `?mes=${mesAtual}&ano=${anoAtual}`;
  } else if (filtro === 'ano') {
    url += `?ano=${anoAtual}`;
  }

  fetch(url)
    .then(response => response.json())
    .then(data => {
      const categorias = data.map(item => item.categoria);
      const valores = data.map(item => item.total);
      const cores = [
        '#0066ff', '#00c853', '#ffab00', '#ff3d00',
        '#6200ea', '#00bcd4', '#607d8b', '#8bc34a',
        '#f44336', '#9c27b0', '#3f51b5', '#795548'
      ];

      if (chartPizza) chartPizza.destroy();

      chartPizza = new Chart(document.getElementById('graficoCategorias'), {
        type: 'doughnut',
        data: {
          labels: categorias,
          datasets: [{
            label: 'Total por Categoria',
            data: valores,
            backgroundColor: cores,
            borderColor: '#fff',
            borderWidth: 2
          }]
        },
        options: {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right',
      align: 'start',
      labels: {
        font: { size: 13 },
        boxWidth: 18,
        padding: 12
      }
    },
    tooltip: {
      callbacks: {
        label: context => {
          const valor = context.parsed || 0;
          return `${context.label}: R$ ${valor.toLocaleString('pt-BR', { minimumFractionDigits: 2 })}`;
        }
      },
      backgroundColor: 'rgba(0,0,0,0.7)',
      titleFont: { size: 14 },
      bodyFont: { size: 13 },
      padding: 10
    }
  },
  onClick: (evt, elements) => {
    if (elements.length > 0) {
      const index = elements[0].index;
      const categoriaSelecionada = chartPizza.data.labels[index];
      mostrarLancamentosFiltrados({ tipo: 'categoria', valor: categoriaSelecionada });
    }
  }
}

      });
    });
}

// Inicializa gráfico
carregarGraficoCategorias();

// Atualiza ao trocar filtro
document.getElementById('filtro-categoria').addEventListener('change', e => {
  carregarGraficoCategorias(e.target.value);
});
function mostrarLancamentosFiltrados(filtro) {
    let url = `/contas-a-pagar/api/lancamentos_filtrados?tipo=${filtro.tipo}&valor=${filtro.valor}`;

    if (filtro.mes && filtro.ano) {
        url += `&mes=${filtro.mes}&ano=${filtro.ano}`;
    }

    // Exibe um loader enquanto carrega
    const modalBody = document.getElementById('modal-body');
    modalBody.innerHTML = '<div class="loading-modal"><i class="fas fa-circle-notch fa-spin"></i> Carregando...</div>';

    fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`Erro HTTP: ${response.status}`);
            }
            return response.json();
        })
        .then(data => {
            // Verifica se os dados são válidos
            if (!Array.isArray(data)) {
                throw new Error("Formato de dados inválido");
            }

            // Processa os dados para garantir que não há NaN
            const lancamentos = data.map(item => ({
                ...item,
                valor: isNaN(item.valor) ? 0.0 : item.valor,
                pago: isNaN(item.pago) ? 0.0 : item.pago
            }));

            const title = filtro.titulo ||
                         (filtro.tipo === 'mes' ? `Lançamentos de ${filtro.valor}` :
                         `Lançamentos em ${filtro.valor}`);

            document.getElementById('modal-title').textContent = title;

            if (lancamentos.length === 0) {
                modalBody.innerHTML = '<p class="no-data">Nenhum lançamento encontrado</p>';
            } else {
                // Cria a tabela com os lançamentos
                let html = `
                    <table class="modal-table">
                        <thead>
                            <tr>
                                <th>Fornecedor</th>
                                <th>Categoria</th>
                                <th>Vencimento</th>
                                <th>Valor</th>
                                <th>Status</th>
                            </tr>
                        </thead>
                        <tbody>
                `;

                lancamentos.forEach(item => {
                    html += `
                        <tr>
                            <td>${item.fornecedor}</td>
                            <td>${item.categoria}</td>
                            <td>${item.vencimento}</td>
                            <td>R$ ${item.valor.toFixed(2).replace('.', ',')}</td>
                            <td class="status-${item.status.toLowerCase()}">${item.status}</td>
                        </tr>
                    `;
                });

                html += `</tbody></table>`;
                modalBody.innerHTML = html;
            }

            // Exibe o modal
            document.getElementById('modal-lancamentos').style.display = 'flex';
        })
        .catch(error => {
            console.error("Erro ao carregar lançamentos:", error);
            modalBody.innerHTML = `
                <div class="error-modal">
                    <i class="fas fa-exclamation-triangle"></i>
                    <p>Erro ao carregar os lançamentos</p>
                </div>
            `;
        });
}

    function fecharModal() {
        document.getElementById('modal-lancamentos').style.display = 'none';
    }

// Remova a função de dentro do event listener
document.getElementById('btn-exportar-pdf').addEventListener('click', () => {
  const filtro = document.getElementById('modal-title').textContent;
const periodo = `mes=${currentMonth}&ano=${currentYear}`;
const url = `/contas-a-pagar/pdf?filtro=${encodeURIComponent(filtro)}&${periodo}`;
  window.open(url, '_blank');
});