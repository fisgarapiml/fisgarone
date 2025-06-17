document.addEventListener('DOMContentLoaded', function() {
  // Gráfico de Vendas Diárias
  if (document.getElementById('graficoVendas')) {
  const ctxVendas = document.getElementById('graficoVendas').getContext('2d');
  const labels = dashboardData.vendasDiarias.map(x => x.dia);
  const atual = dashboardData.vendasDiarias.map(x => x.valor);
  const anterior = dashboardData.vendasDiarias.map(x => x.valor_anterior);

  // Fundo 3D com gradiente radial
  const gradient = ctxVendas.createRadialGradient(80, 60, 10, 200, 120, 450);
  gradient.addColorStop(0, '#e0fffa');       // azul turquesa claro
  gradient.addColorStop(1, '#d1e2f5');       // azul mais escuro

  ctxVendas.save();
  ctxVendas.globalAlpha = 0.7;
  ctxVendas.fillStyle = gradient;
  ctxVendas.fillRect(0, 0, ctxVendas.canvas.width, ctxVendas.canvas.height);
  ctxVendas.restore();

  new Chart(ctxVendas, {
    type: 'line',
    data: {
      labels: labels,
      datasets: [
        {
          label: 'Vendas Atual',
          data: atual,
          borderColor: 'rgba(0, 200, 150, 1)',
          backgroundColor: 'rgba(0, 200, 150, 0.08)',
          borderWidth: 2,
          fill: true,
          tension: 0.2,
          pointRadius: 4,
          pointHoverRadius: 7
        },
        {
          label: 'Mesmo Dia - Mês Anterior',
          data: anterior,
          borderColor: '#ff9800',
          backgroundColor: 'rgba(255,152,0,0.10)',
          borderWidth: 2,
          fill: false,
          borderDash: [5,4],
          tension: 0.2,
          pointRadius: 4,
          pointHoverRadius: 7
        }
      ]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          display: true,
          position: 'top',
          labels: {
            color: '#0f2235', // Azul escuro para destacar, pode trocar!
            font: {
              size: 14,
              weight: 'bold'
            },
            padding: 20,
            boxWidth: 20,
            boxHeight: 12
          }
        },
        tooltip: {
          enabled: true,
          mode: 'index',
          intersect: false,
          backgroundColor: '#00e5cf', // Fundo azul turquesa do tooltip
          titleColor: '#FF6A00',      // Laranja Shopee no título
          bodyColor: '#222',          // Texto preto no corpo
          borderColor: '#FF6A00',
          borderWidth: 2,
          callbacks: {
            label: function(context) {
              const i = context.dataIndex;
              const atual_v = atual[i];
              const anterior_v = anterior[i];
              const variacao = anterior_v > 0 ? (((atual_v - anterior_v) / anterior_v) * 100).toFixed(1) : '0.0';
              if (context.datasetIndex === 0) {
                return [
                  `Vendas Atual: R$ ${atual_v.toLocaleString('pt-BR', {minimumFractionDigits:2})}`,
                  `Mesmo Dia Mês Ant.: R$ ${anterior_v.toLocaleString('pt-BR', {minimumFractionDigits:2})}`,
                  `Variação: ${variacao > 0 ? '+' : ''}${variacao}%`
                ];
              } else {
                return `Mês Anterior: R$ ${anterior_v.toLocaleString('pt-BR', {minimumFractionDigits:2})}`;
              }
            }
          }
        }
      },
      interaction: {
        mode: 'index',
        intersect: false
      },
      scales: {
        x: {
          grid: { display: false, drawBorder: false },
          ticks: {
            color: '#333',
            font: { size: 12, weight: 'bold' }
          }
        },
        y: {
          beginAtZero: true,
          grid: { display: false, drawBorder: false },
          ticks: {
            color: '#222',
            font: { size: 13, weight: 'bold' }
          }
        }
      }
    }
  });
}


  // Gráfico Top Produtos
  if (document.getElementById('graficoTopProdutos')) {
    const ctxTop = document.getElementById('graficoTopProdutos').getContext('2d');
    const labels = dashboardData.topProdutos.map(x => x.SKU);
    const atual = dashboardData.topProdutos.map(x => x.valor);
    const anterior = dashboardData.topProdutos.map(x => x.valor_anterior);

    new Chart(ctxTop, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [
          {
            label: 'Atual',
            data: atual,
            backgroundColor: 'rgba(0, 200, 150, 0.7)',
            borderColor: 'rgba(0, 200, 150, 1)',
            borderWidth: 1
          },
          {
            label: 'Mês Anterior',
            data: anterior,
            backgroundColor: 'rgba(255,152,0,0.6)',
            borderColor: '#ff9800',
            borderWidth: 1
          }
        ]
      },
      options: {
  responsive: true,
  plugins: {
    legend: { display: true, position: 'top' },
    tooltip: {
      enabled: true,
      mode: 'index',         // <<< ESSENCIAL
      intersect: false,      // <<< ESSENCIAL
      callbacks: {
              label: function(context) {
                const i = context.dataIndex;
                const atual_v = atual[i];
                const anterior_v = anterior[i];
                const variacao = anterior_v > 0 ? (((atual_v - anterior_v) / anterior_v) * 100).toFixed(1) : '0.0';
                if (context.datasetIndex === 0) {
                  return [
                    `Atual: R$ ${atual_v.toLocaleString('pt-BR', {minimumFractionDigits:2})}`,
                    `Mês Anterior: R$ ${anterior_v.toLocaleString('pt-BR', {minimumFractionDigits:2})}`,
                    `Variação: ${variacao > 0 ? '+' : ''}${variacao}%`
                  ];
                } else {
                  return `Mês Anterior: R$ ${anterior_v.toLocaleString('pt-BR', {minimumFractionDigits:2})}`;
                }
              }
            }
          }
        },
        interaction: {
    mode: 'index',         // <<< ESSENCIAL
    intersect: false,      // <<< ESSENCIAL
  },
        scales: {
          x: { beginAtZero: true }
        }
      }
    });
  }
});


// ---- MODAL DOS CARDS ----
window.abrirModal = function(tipo) {
  const modal = document.getElementById('premiumModal');
  const titulo = document.getElementById('modalTitle');
  const conteudo = document.getElementById('modalContent');
  let html = '', title = '';
  const r = dashboardData.resumo;

  switch(tipo) {
    case 'faturamento':
      title = '💰 Detalhes do Faturamento';
      html = `
        <div class="modal-details">
          <div class="detail-item"><span class="detail-label">Total Atual:</span><span class="detail-value">R$ ${r.faturamento}</span></div>
          <div class="detail-item"><span class="detail-label">Período Anterior:</span><span class="detail-value">R$ ${r.faturamento_anterior}</span></div>
          <div class="detail-item highlight ${r.faturamento_dif >= 0 ? 'up' : 'down'}">
            <span class="detail-label">Variação:</span><span class="detail-value">${r.faturamento_dif >= 0 ? '▲' : '▼'} ${r.faturamento_dif}%</span>
          </div>
          <div class="detail-item"><span class="detail-label">Período Equivalente:</span><span class="detail-value">${r.faturamento_equivalente_pct}%</span></div>
          <p class="modal-info">O faturamento considera o valor total das vendas brutas, sem dedução de taxas ou devoluções.</p>
        </div>
      `;
      break;
    case 'unidades':
      title = '📦 Detalhes das Unidades Vendidas';
      html = `
        <div class="modal-details">
          <div class="detail-item"><span class="detail-label">Total Atual:</span><span class="detail-value">${r.unidades}</span></div>
          <div class="detail-item"><span class="detail-label">Período Anterior:</span><span class="detail-value">${r.unidades_anterior}</span></div>
          <div class="detail-item highlight ${r.unidades_dif >= 0 ? 'up' : 'down'}">
            <span class="detail-label">Variação:</span><span class="detail-value">${r.unidades_dif >= 0 ? '▲' : '▼'} ${r.unidades_dif}%</span>
          </div>
          <p class="modal-info">Unidades vendidas representam a quantidade total de itens comercializados, considerando todos os SKUs.</p>
        </div>
      `;
      break;
    case 'pedidos':
      title = '🧾 Detalhes dos Pedidos';
      html = `
        <div class="modal-details">
          <div class="detail-item"><span class="detail-label">Total Atual:</span><span class="detail-value">${r.pedidos}</span></div>
          <div class="detail-item"><span class="detail-label">Período Anterior:</span><span class="detail-value">${r.pedidos_anterior}</span></div>
          <div class="detail-item highlight ${r.pedidos_dif >= 0 ? 'up' : 'down'}">
            <span class="detail-label">Variação:</span><span class="detail-value">${r.pedidos_dif >= 0 ? '▲' : '▼'} ${r.pedidos_dif}%</span>
          </div>
          <p class="modal-info">Cada pedido representa uma compra única realizada pelo cliente, podendo conter múltiplos itens.</p>
        </div>
      `;
      break;
    case 'ticket':
      title = '📊 Detalhes do Ticket Médio';
      html = `
        <div class="modal-details">
          <div class="detail-item"><span class="detail-label">Ticket Atual:</span><span class="detail-value">R$ ${r.ticket_medio}</span></div>
          <div class="detail-item"><span class="detail-label">Ticket Anterior:</span><span class="detail-value">R$ ${r.ticket_medio_anterior}</span></div>
          <div class="detail-item highlight ${r.ticket_medio_dif >= 0 ? 'up' : 'down'}">
            <span class="detail-label">Variação:</span><span class="detail-value">${r.ticket_medio_dif >= 0 ? '▲' : '▼'} ${r.ticket_medio_dif}%</span>
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

  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
};

window.fecharModalPremium = function() {
  const modal = document.getElementById('premiumModal');
  modal.style.display = 'none';
  document.body.style.overflow = 'auto';
};

// Fecha modal no esc ou click fora
window.addEventListener('keydown', function(e) {
  if(e.key === "Escape") window.fecharModalPremium();
});
window.addEventListener('click', function(event) {
  const modal = document.getElementById('premiumModal');
  if (event.target === modal) window.fecharModalPremium();
});

// ---- EXPORTAÇÕES DO MODAL ----
window.exportarModal = function(tipo) {
  if(tipo === 'excel') {
    exportarResumoExcel();
  } else if(tipo === 'pdf') {
    exportarResumoPDF();
  }
}

function exportarResumoExcel() {
  const r = dashboardData.resumo;
  let csv = [
    ["Indicador", "Atual", "Anterior", "Variação (%)"],
    ["Faturamento", r.faturamento, r.faturamento_anterior, r.faturamento_dif],
    ["Unidades", r.unidades, r.unidades_anterior, r.unidades_dif],
    ["Pedidos", r.pedidos, r.pedidos_anterior, r.pedidos_dif],
    ["Ticket Médio", r.ticket_medio, r.ticket_medio_anterior, r.ticket_medio_dif],
  ];
  let csvContent = "data:text/csv;charset=utf-8," + csv.map(e=>e.join(";")).join("\n");
  let link = document.createElement("a");
  link.setAttribute("href", encodeURI(csvContent));
  link.setAttribute("download", "dashboard_shopee_resumo.csv");
  document.body.appendChild(link); link.click(); document.body.removeChild(link);
}

function exportarResumoPDF() {
  window.print();
}

// ========== FIM DASHBOARD.JS ==========