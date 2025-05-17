const video = document.getElementById('video');
const statusEl = document.getElementById('status');
const bip = document.getElementById('bip');

// Ativar webcam
navigator.mediaDevices.getUserMedia({ video: true })
    .then(stream => {
        video.srcObject = stream;
        detectarERegistrar();
    })
    .catch(err => {
        statusEl.innerText = 'Erro ao acessar câmera.';
    });

// Simular detecção + contagem + registro
function detectarERegistrar() {
    let segundos = 5;
    statusEl.innerText = `Reconhecimento confirmado! Registrando ponto em ${segundos}...`;
    const countdown = setInterval(() => {
        segundos--;
        statusEl.innerText = `Registrando ponto em ${segundos}...`;
        if (segundos === 0) {
            clearInterval(countdown);
            registrarPonto();
        }
    }, 1000);
}

function registrarPonto() {
    fetch('/registrar_ponto', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            funcionario: 'João da Silva',
            tipo: 'Entrada'
        })
    })
    .then(res => res.json())
    .then(data => {
        bip.play();
        statusEl.innerHTML = `<span class="ok">✅ Ponto registrado com sucesso às ${data.hora} (${data.data})</span>`;
    })
    .catch(() => {
        statusEl.innerText = 'Erro ao registrar ponto.';
    });
}
