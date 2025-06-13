// shopee_charts.js - Versão Futurista com ApexCharts

// 1. Configurações Globais
const chartSettings = {
  fontFamily: 'Orbitron, sans-serif',
  foreColor: '#FFFFFF',
  toolbar: { show: false },
  animations: {
    enabled: true,
    easing: 'easeinout',
    speed: 800
  }
};

// 2. Inicialização dos Gráficos
function initCharts(data) {
  // Destrói gráficos existentes se houver
  const chartElements = document.querySelectorAll('.chart-wrapper canvas');
  chartElements.forEach(canvas => {
    if (canvas.chart) {
      canvas.chart.destroy();
    }
  });

  // Gráfico 1: Faturamento Diário (Full Width)
  if (data.dailyRevenue) {
    const dailyChart = new ApexCharts(
      document.querySelector("#daily-revenue-chart"),
      getDailyRevenueConfig(data.dailyRevenue)
    );
    dailyChart.render();
    document.querySelector("#daily-revenue-chart").chart = dailyChart;
  }

  // Gráfico 2: Top Produtos (3D Effect)
  if (data.topProducts) {
    const topProductsChart = new ApexCharts(
      document.querySelector("#top-products-chart"),
      getTopProductsConfig(data.topProducts)
    );
    topProductsChart.render();
    document.querySelector("#top-products-chart").chart = topProductsChart;
  }

  // Gráfico 3: Transportadoras (Donut 3D)
  if (data.shipping) {
    const shippingChart = new ApexCharts(
      document.querySelector("#shipping-chart"),
      getShippingConfig(data.shipping)
    );
    shippingChart.render();
    document.querySelector("#shipping-chart").chart = shippingChart;
  }

  // Gráfico 4: Métricas (Radar Futurista)
  if (data.metrics) {
    const metricsChart = new ApexCharts(
      document.querySelector("#metrics-chart"),
      getMetricsConfig(data.metrics)
    );
    metricsChart.render();
    document.querySelector("#metrics-chart").chart = metricsChart;
  }
}

// 3. Configurações Específicas para Cada Gráfico

// Gráfico de Faturamento Diário (Área com Efeito Neon)
function getDailyRevenueConfig(data) {
  return {
    chart: {
      ...chartSettings,
      type: 'area',
      height: '100%',
      sparkline: { enabled: false },
      background: 'transparent'
    },
    series: [{
      name: 'Faturamento',
      data: data.data
    }],
    colors: ['#00FF9D'],
    stroke: {
      width: 3,
      curve: 'smooth'
    },
    fill: {
      type: 'gradient',
      gradient: {
        shade: 'dark',
        gradientToColors: ['#FF6B00'],
        shadeIntensity: 1,
        type: 'vertical',
        opacityFrom: 0.7,
        opacityTo: 0.1,
        stops: [0, 100]
      }
    },
    xaxis: {
      categories: data.labels,
      labels: {
        style: { colors: '#FFFFFF' }
      }
    },
    yaxis: {
      labels: {
        formatter: (value) => `R$ ${value.toLocaleString('pt-BR')}`,
        style: { colors: '#FFFFFF' }
      }
    },
    tooltip: {
      theme: 'dark',
      y: {
        formatter: (value) => `R$ ${value.toLocaleString('pt-BR')}`
      }
    },
    markers: {
      size: 5,
      colors: ['#FF6B00'],
      strokeWidth: 0
    }
  };
}

// Gráfico de Top Produtos (Barras 3D)
function getTopProductsConfig(data) {
  return {
    chart: {
      ...chartSettings,
      type: 'bar',
      height: '100%',
      stacked: false,
      background: 'transparent'
    },
    plotOptions: {
      bar: {
        borderRadius: 8,
        columnWidth: '60%',
        dataLabels: { position: 'top' },
        distributed: true
      }
    },
    series: [{
      name: 'Lucro',
      data: data.data
    }],
    colors: ['#FF6B00', '#00FF9D', '#00B8FF', '#FF00AA', '#AA00FF'],
    dataLabels: {
      enabled: true,
      style: {
        fontSize: '12px',
        fontWeight: 'bold'
      },
      formatter: (val) => `R$ ${val.toLocaleString('pt-BR')}`,
      offsetY: -20
    },
    xaxis: {
      categories: data.labels,
      labels: {
        style: {
          fontSize: '12px',
          colors: '#FFFFFF'
        }
      }
    },
    yaxis: {
      labels: {
        formatter: (val) => `R$ ${val.toLocaleString('pt-BR')}`,
        style: { colors: '#FFFFFF' }
      }
    },
    tooltip: {
      theme: 'dark',
      y: {
        formatter: (val) => `R$ ${val.toLocaleString('pt-BR')}`
      }
    }
  };
}

// Gráfico de Transportadoras (Donut 3D)
function getShippingConfig(data) {
  return {
    chart: {
      ...chartSettings,
      type: 'donut',
      height: '100%',
      background: 'transparent'
    },
    series: data.data,
    labels: data.labels,
    colors: ['#FF6B00', '#00FF9D', '#00B8FF', '#FF00AA', '#AA00FF'],
    plotOptions: {
      pie: {
        donut: {
          size: '65%',
          labels: {
            show: true,
            total: {
              show: true,
              label: 'Total',
              color: '#FFFFFF',
              formatter: () => `${data.data.reduce((a, b) => a + b, 0)} Pedidos`
            }
          }
        }
      }
    },
    dataLabels: {
      enabled: true,
      style: {
        fontSize: '14px',
        fontWeight: 'bold'
      },
      dropShadow: {
        enabled: true,
        top: 1,
        left: 1,
        blur: 1,
        opacity: 0.45
      }
    },
    legend: {
      position: 'right',
      labels: {
        colors: '#FFFFFF',
        useSeriesColors: false
      }
    },
    tooltip: {
      theme: 'dark',
      y: {
        formatter: (val) => `${val} Pedidos`
      }
    }
  };
}

// 4. Função para Atualizar Dados
function updateCharts(newData) {
  // Atualiza cada gráfico se existir
  const charts = {
    daily: document.querySelector("#daily-revenue-chart")?.chart,
    products: document.querySelector("#top-products-chart")?.chart,
    shipping: document.querySelector("#shipping-chart")?.chart,
    metrics: document.querySelector("#metrics-chart")?.chart
  };

  if (charts.daily && newData.dailyRevenue) {
    charts.daily.updateSeries([{
      data: newData.dailyRevenue.data
    }]);
    charts.daily.updateOptions({
      xaxis: { categories: newData.dailyRevenue.labels }
    });
  }

  if (charts.products && newData.topProducts) {
    charts.products.updateSeries([{
      data: newData.topProducts.data
    }]);
    charts.products.updateOptions({
      xaxis: { categories: newData.topProducts.labels }
    });
  }

  if (charts.shipping && newData.shipping) {
    charts.shipping.updateSeries(newData.shipping.data);
    charts.shipping.updateOptions({
      labels: newData.shipping.labels
    });
  }
}

// 5. Exporta funções para uso global
window.initCharts = initCharts;
window.updateCharts = updateCharts;