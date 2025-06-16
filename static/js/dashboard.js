document.addEventListener('DOMContentLoaded', function() {
  // Inicializar tooltips
  initTooltips();

  // Inicializar gráficos
  initCharts();

  // Configurar eventos dos cards
  setupCardInteractions();

  // Configurar eventos dos botões de filtro
  setupFilterButtons();

  // Configurar eventos da tabela
  setupTableSorting();
});

function initTooltips() {
  // Tooltip para os cards
  const cards = document.querySelectorAll('.neon-card');
  cards.forEach(card => {
    card.addEventListener('mousemove', function(e) {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;

      card.style.setProperty('--mouse-x', x);
      card.style.setProperty('--mouse-y', y);
    });
  });
}

function initCharts() {
  // Gráfico de vendas comparativo
  const ctxVendas = document.getElementById('chartVendasComparativo').getContext('2d');
  const vendasChart = new Chart(ctxVendas, {
    type: 'line',
    data: {
      labels: dashboardData.vendasDiarias.map(v => v.data),
      datasets: [
        {
          label: 'Hoje',
          data: dashboardData.vendasDiarias.map(v => v.valor_total),
          borderColor: '#00c896',
          backgroundColor: 'rgba(0, 200, 150, 0.1)',
          borderWidth: 3,
          tension: 0.3,
          fill: true,
          pointBackgroundColor: '#fff',
          pointBorderColor: '#00c896',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7
        },
        {
          label: 'Dia Anterior',
          data: dashboardData.comparativo.map(v => v.valor_total),
          borderColor: '#ff6600',
          backgroundColor: 'rgba(255, 102, 0, 0.1)',
          borderWidth: 3,
          borderDash: [5, 5],
          tension: 0.3,
          fill: true,
          pointBackgroundColor: '#fff',
          pointBorderColor: '#ff6600',
          pointBorderWidth: 2,
          pointRadius: 5,
          pointHoverRadius: 7
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: 'top',
          labels: {
            font: {
              size: 14
            },
            padding: 20,
            usePointStyle: true,
            pointStyle: 'circle'
          }
        },
        tooltip: {
          backgroundColor: 'rgba(0, 0, 0, 0.8)',
          titleColor: '#fff',
          bodyColor: '#fff',
          borderColor: 'rgba(255, 255, 255, 0.1)',
          borderWidth: 1,
          padding: 30,
          usePointStyle: true,
          callbacks: {
            label: function(context) {
              let label = context.dataset.label || '';
              if (label) {
                label += ': ';
              }
              label += 'R$ ' + context.raw.toLocaleString('pt-BR', { minimumFractionDigits: 2 });
              return label;
            }
          }
        }
      },
      scales: {
  x: {
    grid: { display: false, drawBorder: false }
  },
  y: {
    grid: { display: false, drawBorder: false }
  }
}

        },
        y: {
          beginAtZero: true,
          grid: {
            color: 'rgba(0, 0, 0, 0.05)'
          },
          ticks: {
            callback: function(value) {
              return 'R$ ' + value.toLocaleString('pt-BR');
            }
          }
        }
      },
      interaction: {
        intersect: false,
        mode: 'index'
      }
    }
  });




function setupCardInteractions() {
  // Animar barras de progresso quando visíveis
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const card = entry.target;
        const percent = card.getAttribute('data-percent');
        const progressBar = card.querySelector('.progress-bar');

        if (progressBar) {
          progressBar.style.width = `${percent}%`;
          card.style.setProperty('--percent', percent);
        }

        observer.unobserve(card);
      }
    });
  }, { threshold: 0.1 });

  document.querySelectorAll('.neon-card').forEach(card => {
    observer.observe(card);
  });
}

function setupFilterButtons() {
  // Botões de período do gráfico
  const periodButtons = document.querySelectorAll('[data-period]');
  periodButtons.forEach(button => {
    button.addEventListener('click', function() {
      periodButtons.forEach(btn => btn.classList.remove('active'));
      this.classList.add('active');
      // Aqui você implementaria a lógica para alterar o período do gráfico
      console.log('Período selecionado:', this.dataset.period);
    });
  });

  // Botões de métrica do top produtos
  const metricButtons = document.querySelectorAll('[data-metric]');
  metricButtons.forEach(button => {
    button.addEventListener('click', function() {
      metricButtons.forEach(btn => btn.classList.remove('active'));
      this.classList.add('active');
      // Aqui você implementaria a lógica para alterar a métrica do gráfico
      console.log('Métrica selecionada:', this.dataset.metric);
    });
  });

  // Botão avançado
  document.getElementById('btn-advanced').addEventListener('click', function() {
    alert('Filtros avançados serão implementados em breve!');
  });
}

function setupTableSorting() {
  const sortButtons = document.querySelectorAll('[data-sort]');
  sortButtons.forEach(button => {
    button.addEventListener('click', function() {
      sortButtons.forEach(btn => btn.classList.remove('active'));
      this.classList.add('active');

      const sortBy = this.dataset.sort;
      const tbody = document.querySelector('.sales-table tbody');
      const rows = Array.from(tbody.querySelectorAll('tr'));

      rows.sort((a, b) => {
        const aValue = sortBy === 'recent' ?
          a.cells[2].textContent :
          parseFloat(a.cells[1].textContent.replace('R$ ', '').replace(',', '.'));

        const bValue = sortBy === 'recent' ?
          b.cells[2].textContent :
          parseFloat(b.cells[1].textContent.replace('R$ ', '').replace(',', '.'));

        return sortBy === 'recent' ?
          bValue.localeCompare(aValue) :
          bValue - aValue;
      });

      // Remover todas as linhas
      rows.forEach(row => tbody.removeChild(row));

      // Adicionar linhas ordenadas
      rows.forEach(row => tbody.appendChild(row));
    });
  });
}

// Funções do Modal
function abrirModal(tipo) {
  const modal = document.getElementById('premiumModal');
  const titulo = document.getElementById('modalTitle');
  const conteudo = document.getElementById('modalContent');

  let html = '';
  let title = '';

  switch(tipo) {
    case 'faturamento':
      title = '💰 Detalhes do Faturamento';
      html = `
        <div class="modal-details">
          <div class="detail-item">
            <span class="detail-label">Total Atual:</span>
            <span class="detail-value">R$ ${dashboardData.resumo.faturamento}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Período Anterior:</span>
            <span class="detail-value">R$ ${dashboardData.resumo.faturamento_anterior}</span>
          </div>
          <div class="detail-item highlight ${dashboardData.resumo.faturamento_dif >= 0 ? 'up' : 'down'}">
            <span class="detail-label">Variação:</span>
            <span class="detail-value">${dashboardData.resumo.faturamento_dif >= 0 ? '▲' : '▼'} ${dashboardData.resumo.faturamento_dif}%</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Período Equivalente:</span>
            <span class="detail-value">${dashboardData.resumo.faturamento_equivalente_pct}%</span>
          </div>

          <div class="modal-chart">
            <canvas id="modalFaturamentoChart"></canvas>
          </div>

          <p class="modal-info">O faturamento considera o valor total das vendas brutas, sem dedução de taxas ou devoluções.</p>
        </div>
      `;
      break;

    case 'unidades':
      title = '📦 Detalhes das Unidades Vendidas';
      html = `
        <div class="modal-details">
          <div class="detail-item">
            <span class="detail-label">Total Atual:</span>
            <span class="detail-value">${dashboardData.resumo.unidades}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Período Anterior:</span>
            <span class="detail-value">${dashboardData.resumo.unidades_anterior}</span>
          </div>
          <div class="detail-item highlight ${dashboardData.resumo.unidades_dif >= 0 ? 'up' : 'down'}">
            <span class="detail-label">Variação:</span>
            <span class="detail-value">${dashboardData.resumo.unidades_dif >= 0 ? '▲' : '▼'} ${dashboardData.resumo.unidades_dif}%</span>
          </div>

          <div class="modal-chart">
            <canvas id="modalUnidadesChart"></canvas>
          </div>

          <p class="modal-info">Unidades vendidas representam a quantidade total de itens comercializados, considerando todos os SKUs.</p>
        </div>
      `;
      break;

    case 'pedidos':
      title = '🧾 Detalhes dos Pedidos';
      html = `
        <div class="modal-details">
          <div class="detail-item">
            <span class="detail-label">Total Atual:</span>
            <span class="detail-value">${dashboardData.resumo.pedidos}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Período Anterior:</span>
            <span class="detail-value">${dashboardData.resumo.pedidos_anterior}</span>
          </div>
          <div class="detail-item highlight ${dashboardData.resumo.pedidos_dif >= 0 ? 'up' : 'down'}">
            <span class="detail-label">Variação:</span>
            <span class="detail-value">${dashboardData.resumo.pedidos_dif >= 0 ? '▲' : '▼'} ${dashboardData.resumo.pedidos_dif}%</span>
          </div>

          <div class="modal-chart">
            <canvas id="modalPedidosChart"></canvas>
          </div>

          <p class="modal-info">Cada pedido representa uma compra única realizada pelo cliente, podendo conter múltiplos itens.</p>
        </div>
      `;
      break;

    case 'ticket':
      title = '📊 Detalhes do Ticket Médio';
      html = `
        <div class="modal-details">
          <div class="detail-item">
            <span class="detail-label">Ticket Atual:</span>
            <span class="detail-value">R$ ${dashboardData.resumo.ticket_medio}</span>
          </div>
          <div class="detail-item">
            <span class="detail-label">Ticket Anterior:</span>
            <span class="detail-value">R$ ${dashboardData.resumo.ticket_medio_anterior}</span>
          </div>
          <div class="detail-item highlight ${dashboardData.resumo.ticket_medio_dif >= 0 ? 'up' : 'down'}">
            <span class="detail-label">Variação:</span>
            <span class="detail-value">${dashboardData.resumo.ticket_medio_dif >= 0 ? '▲' : '▼'} ${dashboardData.resumo.ticket_medio_dif}%</span>
          </div>

          <div class="modal-chart">
            <canvas id="modalTicketChart"></canvas>
          </div>

          <p class="modal-info">O ticket médio é calculado dividindo o faturamento total pelo número de pedidos.</p>
        </div>
      `;
      break;

    default:
      title = 'Detalhes';
      html = '<p>Selecione um indicador para visualizar os detalhes.</p>';
  }

  titulo.textContent = title;
  conteudo.innerHTML = html;

  // Inicializar gráficos do modal
  initModalCharts(tipo);

  // Mostrar modal
  modal.style.display = 'block';
  document.body.style.overflow = 'hidden';
}

function fecharModalPremium() {
  const modal = document.getElementById('premiumModal');
  modal.style.display = 'none';
  document.body.style.overflow = 'auto';
}

function initModalCharts(tipo) {
  // Implementar gráficos específicos para cada modal
  // Esta é uma implementação básica - você pode expandir conforme necessário
  const ctx = document.getElementById(`modal${tipo.charAt(0).toUpperCase() + tipo.slice(1)}Chart`);
  if (!ctx) return;

  new Chart(ctx, {
    type: 'line',
    data: {
      labels: ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun'],
      datasets: [{
        label: tipo.charAt(0).toUpperCase() + tipo.slice(1),
        data: [12, 19, 3, 5, 2, 3],
        borderColor: '#00c896',
        backgroundColor: 'rgba(0, 200, 150, 0.1)',
        borderWidth: 2,
        tension: 0.1,
        fill: true
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: false
        }
      }
    }
  });
}

function exportarDashboard() {
  // Implementar exportação para PDF/Excel
  alert('Exportação para PDF/Excel será implementada em breve!');
}

function compararPeriodos() {
  // Implementar comparação de períodos
  alert('Comparação de períodos será implementada em breve!');
}

function verDetalhes() {
  // Implementar visualização detalhada
  alert('Visualização detalhada será implementada em breve!');
}

// Fechar modal ao clicar fora
window.addEventListener('click', function(event) {
  const modal = document.getElementById('premiumModal');
  if (event.target === modal) {
    fecharModalPremium();
  }
});