// Configuração Global ApexCharts
Apex = {
  chart: {
    fontFamily: 'Roboto, sans-serif',
    foreColor: '#E0E0E0',
    toolbar: { show: false },
    animations: {
      enabled: true,
      easing: 'easeinout',
      speed: 800
    }
  },
  colors: ['#FF6B00', '#00C4FF', '#00FF9D', '#FFB800'],
  dataLabels: { enabled: false },
  stroke: { curve: 'smooth', width: 3 },
  grid: { borderColor: 'rgba(255, 255, 255, 0.1)' },
  tooltip: {
    theme: 'dark',
    x: { format: 'dd MMM yyyy' }
  }
};

// Inicialização dos Gráficos
function initProfessionalCharts(data) {
  // 1. Gráfico Principal de Performance
  const mainChart = new ApexCharts(document.querySelector("#main-performance-chart"), {
    series: [{
      name: 'Faturamento',
      data: data.dailyRevenue
    }, {
      name: 'Lucro',
      data: data.dailyProfit
    }],
    chart: {
      type: 'area',
      height: '100%',
      background: 'transparent'
    },
    xaxis: {
      type: 'datetime',
      labels: { datetimeUTC: false }
    },
    yaxis: {
      labels: {
        formatter: (value) => `R$ ${(value/1000).toFixed(1)}k`
      }
    }
  });

  // 2. Gráfico de Top Produtos
  const productsChart = new ApexCharts(document.querySelector("#top-products-chart"), {
    series: [{
      name: 'Lucratividade',
      data: data.topProducts
    }],
    chart: {
      type: 'radialBar',
      height: '100%'
    },
    plotOptions: {
      radialBar: {
        hollow: { size: '50%' },
        dataLabels: {
          name: { fontSize: '14px' },
          value: {
            fontSize: '20px',
            formatter: (val) => `R$ ${val}k`
          }
        }
      }
    }
  });

  // Renderização
  mainChart.render();
  productsChart.render();

  // Armazena referências para atualização
  window.dashboardCharts = { mainChart, productsChart };
}

// Atualização Dinâmica
function updateCharts(newData) {
  if (window.dashboardCharts) {
    window.dashboardCharts.mainChart.updateSeries([
      { name: 'Faturamento', data: newData.dailyRevenue },
      { name: 'Lucro', data: newData.dailyProfit }
    ]);

    window.dashboardCharts.productsChart.updateSeries([
      { data: newData.topProducts }
    ]);
  }
}

// Exporta funções
window.initProfessionalCharts = initProfessionalCharts;
window.updateCharts = updateCharts;