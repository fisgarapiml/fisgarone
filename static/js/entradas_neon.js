// Relógio em tempo real
function updateClock() {
    const now = new Date();
    document.getElementById('clock').innerText = now.toLocaleString('pt-BR', {
        hour: '2-digit', minute: '2-digit', second: '2-digit'
    });
}
setInterval(updateClock, 1000); updateClock();

// Card count-up (animação para os cards de valor)
document.querySelectorAll('[data-countup]').forEach(el => {
    const val = parseFloat(el.innerText.replace(/[^\d,-]/g, '').replace(',', '.')) || 0;
    let curr = 0, steps = 36, i = 0, step = val / steps;
    el.innerText = "0,00";
    function animate() {
        i++;
        curr += step;
        el.innerText = curr.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
        if (i < steps) requestAnimationFrame(animate);
        else el.innerText = val.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    }
    animate();
});

// Gráficos Chart.js
window.addEventListener('DOMContentLoaded', function () {
    // Dados vindos do backend Jinja/Flask
    const labelsGrafico = window.labelsGrafico || [];
    const valoresEntradas = window.valoresEntradas || [];
    const canais = window.canais || [];
    const distribCanais = window.distribCanais || [];

    // Gráfico de evolução das entradas
    if (document.getElementById('entradasChart')) {
        new Chart(document.getElementById('entradasChart').getContext('2d'), {
            type: 'line',
            data: {
                labels: labelsGrafico,
                datasets: [{
                    label: 'Entradas',
                    data: valoresEntradas,
                    borderColor: '#00CFFF',
                    backgroundColor: '#00CFFF22',
                    tension: 0.35,
                    pointRadius: 3,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                plugins: { legend: { display: false } },
                scales: {
                    x: { ticks: { color: '#00CFFF', font: { weight: 'bold' } } },
                    y: { ticks: { color: '#007A9A' }, beginAtZero: true }
                }
            }
        });
    }

    // Gráfico de canais
    if (document.getElementById('pieChart')) {
        new Chart(document.getElementById('pieChart').getContext('2d'), {
            type: 'doughnut',
            data: {
                labels: canais,
                datasets: [{
                    data: distribCanais,
                    backgroundColor: ['#00CFFF', '#FFB800', '#47F487', '#8A76FF', '#FF5271', '#32B8E4', '#B41BFF'],
                    borderWidth: 0
                }]
            },
            options: {
                cutout: 58,
                plugins: { legend: { labels: { color: '#222', font: { weight: 'bold' } } } }
            }
        });
    }
});
