# agente_fisgar.py

import os
import argparse
import sqlite3
import subprocess
import time
import requests
import openai
import textwrap
from datetime import datetime
from pathlib import Path

# Configurar sua API key do OpenAI como variável de ambiente
openai.api_key = os.getenv('OPENAI_API_KEY')

BASE_DIR = Path(__file__).parent.resolve()
DB_PATH = BASE_DIR / 'grupo_fisgar.db'

# Localiza automaticamente o arquivo principal do app (app.py, app.py, etc.)
def find_app_file():
    for fname in os.listdir(BASE_DIR):
        if fname.startswith('app') and fname.endswith('.py'):
            return BASE_DIR / fname
    return None
APP_FILE = find_app_file()

# ------------------------
# Função: gerar CSS base Fisgar Neon Premium
# ------------------------
def gerar_css():
    css_dir = BASE_DIR / 'static' / 'css'
    css_dir.mkdir(parents=True, exist_ok=True)
    fisgar_css = textwrap.dedent(r"""
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
        :root {
          --primary: #0066ff;
          --accent: #00ffaa;
          --text: #2b2d42;
          --bg: #f8faff;
          --card-bg: rgba(255,255,255,0.95);
          --status-success: #00c853;
          --status-warning: #ffab00;
          --status-danger: #ff3d00;
          --status-info: #0066ff;
          --shadow-sm: 0 2px 8px rgba(0,0,0,0.08);
          --shadow-md: 0 4px 20px rgba(0,102,255,0.12);
        }
        body {
          margin: 0;
          font-family: 'Space Grotesk', sans-serif;
          background: var(--bg);
          color: var(--text);
          transition: background 0.3s ease, color 0.3s ease;
        }
        body.dark {
          background: var(--card-bg);
          color: white;
        }
        /* ... restante do CSS ... */
    """ )
    (css_dir / 'estilo_global.css').write_text(fisgar_css, encoding='utf-8')
    print(f"✅ CSS gerado: {css_dir / 'estilo_global.css'}")

# ------------------------
# Função: gerar API de Estoque
# ------------------------
def gerar_api_estoque():
    mod_dir = BASE_DIR / 'modulos' / 'estoque'
    mod_dir.mkdir(parents=True, exist_ok=True)
    api_file = mod_dir / 'api_estoque.py'
    api_code = textwrap.dedent(f"""
        from flask import Blueprint, jsonify
        import sqlite3

        api_estoque = Blueprint('api_estoque', __name__)

        @api_estoque.route('/api/estoque')
        def estoque():
            conn = sqlite3.connect(r'{DB_PATH}')
            cur = conn.cursor()
            total = cur.execute("SELECT SUM(quantidade) FROM produtos_processados").fetchone()[0] or 0
            ok    = cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade >= 10").fetchone()[0]
            baixo = cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade < 10 AND quantidade > 0").fetchone()[0]
            crit  = cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade = 0").fetchone()[0]
            rows  = cur.execute(
                "SELECT codigo,nome,fornecedor,quantidade,data_emissao FROM produtos_processados "
                "WHERE quantidade <= 10 ORDER BY quantidade ASC"
            ).fetchall()
            conn.close()
            detalhe = [
                {{'codigo': r[0], 'nome': r[1], 'fornecedor': r[2], 'estoqueAtual': r[3], 'ultimaEntrada': r[4]}}
                for r in rows
            ]
            return jsonify({{
                'totalItens': total,
                'itensOk': ok,
                'itensBaixos': baixo,
                'itensCriticos': crit,
                'itensCriticosList': detalhe,
                'entradasMensais': [],
                'saidasMensais': [],
                'valoresPorCategoria': []
            }})
    """ )
    api_file.write_text(api_code, encoding='utf-8')
    print(f"✅ API gerada: {api_file}")

# ------------------------
# Função: gerar template dashboard
# ------------------------
def gerar_template_dashboard():
    tmpl_dir = BASE_DIR / 'templates' / 'estoque'
    tmpl_dir.mkdir(parents=True, exist_ok=True)
    dashboard_file = tmpl_dir / 'dashboard.html'
    html = textwrap.dedent("""
        <!DOCTYPE html>
        <html lang="pt-BR">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Neon Finance | Estoque</title>
            <link rel="stylesheet" href="/static/css/estilo_global.css">
            <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        </head>
        <body>
        <div class="sidebar">
            <h2>📦 Estoque</h2>
            <a href="/estoque" class="active">🏠 Dashboard</a>
            <a href="/estoque/inventario">📋 Inventário</a>
            <a href="/estoque/adicionar">➕ Novo Produto</a>
            <button class="btn-outline" onclick="toggleTheme()">🌗 Tema</button>
        </div>
        <main class="container">
            <h1 class="page-title">Dashboard de Estoque</h1>
            <div class="cards-container">
                <!-- cards -->
            </div>
            <div class="charts-container">
                <!-- charts -->
            </div>
            <div class="card">
                <div class="filter-bar">
                    <!-- filters -->
                </div>
                <div class="card-body table-responsive">
                    <table class="data-table" id="tabela-estoque">
                        <thead>
                            <tr><th>Código</th><th>Nome</th><th>Fornecedor</th><th>Qtd</th><th>Última Entrada</th><th>Ações</th></tr>
                        </thead>
                        <tbody></tbody>
                    </table>
                </div>
            </div>
        </main>
        <script>
        async function loadData() {
            const res = await fetch('/api/estoque');
            const data = await res.json();
            document.getElementById('totalItens').textContent = data.totalItens;
            document.getElementById('itensOk').textContent = data.itensOk;
            document.getElementById('itensBaixos').textContent = data.itensBaixos;
            document.getElementById('itensCriticos').textContent = data.itensCriticos;
            const tbody = document.querySelector('#tabela-estoque tbody');
            tbody.innerHTML = '';
            data.itensCriticosList.forEach(i => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>${i.codigo}</td>
                    <td>${i.nome}</td>
                    <td>${i.fornecedor}</td>
                    <td>${i.estoqueAtual}</td>
                    <td>${i.ultimaEntrada}</td>
                    <td><button class='btn-outline' onclick="location.href='/estoque/editar/${i.codigo}'">✏️</button></td>
                `;
                tbody.appendChild(tr);
            });
            new Chart(document.getElementById('movimentacaoChart'), {
                type: 'line',
                data: { labels: ['Jan','Fev','Mar','Abr','Mai','Jun'], datasets: [
                    { label: 'Entradas', data: data.entradasMensais, borderColor: '#00c853', fill: true, tension: 0.3 },
                    { label: 'Saídas',    data: data.saidasMensais,   borderColor: '#0066ff', fill: true, tension: 0.3 }
                ] },
                options: { responsive: true }
            });
            new Chart(document.getElementById('categoriasChart'), {
                type: 'doughnut',
                data: { labels: ['Eletrônicos','Materiais','Peças','Outros'], datasets: [ { data: data.valoresPorCategoria } ] },
                options: { responsive: true, plugins: { legend: { position: 'right' } } }
            });
        }
        function toggleTheme() {
            document.body.classList.toggle('dark');
            localStorage.setItem('tema', document.body.classList.contains('dark') ? 'escuro' : 'claro');
        }
        window.onload = loadData;
        </script>
        </body>
        </html>
    """ )
    dashboard_file.write_text(html, encoding='utf-8')
    print(f"✅ Dashboard gerado: {dashboard_file}")

# ------------------------
# Funções de teste e correção automática
# ------------------------
def iniciar_servidor():
    proc = subprocess.Popen(['python', str(APP_FILE)], cwd=str(BASE_DIR))
    time.sleep(3)
    return proc

def testar_endpoints():
    erros=[]
    for rota in ['/estoque','/estoque/inventario','/estoque/adicionar','/api/estoque']:
        url = f'http://127.0.0.1:5000{rota}'
        try:
            resp = requests.get(url)
        except Exception as e:
            erros.append({'rota': rota, 'error': str(e)})
            continue
        if resp.status_code != 200:
            erros.append({'rota': rota, 'status': resp.status_code})
    return erros

# ... restante do código permanece inalterado ...


def testar_crud():
    sess=requests.Session();erros=[]
    r1=sess.post('http://127.0.0.1:5000/estoque/adicionar',data={'nome':'TEST_AGENTE','quantidade':1})
    if r1.status_code not in (200,302):erros.append({'acao':'adicionar','status':r1.status_code})
    r2=sess.get('http://127.0.0.1:5000/estoque/inventario')
    if 'TEST_AGENTE' not in r2.text:erros.append({'acao':'verificar inventario','error':'Item não encontrado'})
    return erros

def revisar_e_corrigir(erros):
    codigo=Path(__file__).read_text(encoding='utf-8')
    prompt=(f"Erros: {erros}. Corrija o código abaixo sem adicionar recursos extras.")
    resp=openai.ChatCompletion.create(
        model='gpt-4o-mini',
        messages=[{'role':'user','content':codigo+'\n\n'+prompt}],
        temperature=0
    )
    novo=resp.choices[0].message.content
    Path(__file__).write_text(novo,encoding='utf-8')
    print('✅ Código corrigido.')

# ------------------------
# Registrar blueprint no app
# ------------------------
def registrar_blueprint():
    if not APP_FILE: return
    cont=Path(APP_FILE).read_text(encoding='utf-8')
    if 'api_estoque' in cont: return
    lines=cont.splitlines()
    for i,l in enumerate(lines):
        if 'Flask' in l:
            lines.insert(i+1,'from modulos.estoque.api_estoque import api_estoque')
            lines.insert(i+2,'app.register_blueprint(api_estoque)')
            break
    Path(APP_FILE).write_text("\n".join(lines),encoding='utf-8')
    print(f'✅ Blueprint registrado em {APP_FILE}')

# ------------------------
# Pipeline autônomo
# ------------------------
def pipeline_autonomo():
    gerar_css(); gerar_api_estoque(); gerar_template_dashboard(); registrar_blueprint()
    proc=iniciar_servidor(); erros=testar_endpoints()+testar_crud(); proc.terminate()
    if erros: revisar_e_corrigir(erros); print('🔄 Reexecute para validar.')
    else: print('🎉 Pipeline concluído sem erros!')

# ------------------------
# Main
# ------------------------
if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--tarefa',required=True)
    t=p.parse_args().tarefa.lower()
    if 'estoque' in t: pipeline_autonomo()
    else: print('Use: --tarefa "estoque"')
