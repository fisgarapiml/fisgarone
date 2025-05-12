# agente_fisgar.py

import os
import argparse
import sqlite3
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'grupo_fisgar.db')
APP_PATH = os.path.join(BASE_DIR, 'app.py')  # ajuste se necessário

# Identidade Visual Fisgar Neon Premium (CSS Base)
FISGAR_CSS = '''
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&display=swap');
:root { --primary: #0066ff; --accent: #00ffaa; --text: #2b2d42; --bg: #f8faff; --card-bg: rgba(255,255,255,0.95);
  --status-success: #00c853; --status-warning: #ffab00; --status-danger: #ff3d00; --status-info: #0066ff;
  --shadow-sm: 0 2px 8px rgba(0,0,0,0.08); --shadow-md: 0 4px 20px rgba(0,102,255,0.12);
}
body { margin:0; font-family:'Space Grotesk',sans-serif; background: var(--bg); color: var(--text); }
body.dark { background: var(--card-bg); }
.container { max-width:1400px; margin:0 auto; padding:24px; }
.sidebar { position:fixed; top:0; left:0; width:260px; height:100%; background:var(--card-bg); padding:30px; box-shadow:4px 0 10px rgba(0,0,0,0.5); }
.sidebar h2 { color: var(--primary); margin:0 0 20px; }
.sidebar a { display:block; color: var(--primary); text-decoration:none; margin:12px 0; transition:0.3s; }
.sidebar a:hover, .sidebar a.active { color: var(--accent); }
.sidebar button { margin-top:20px; }
main { margin-left:300px; padding:40px; }
.cards-container, .charts-container { display:grid; gap:20px; margin-bottom:24px; }
.cards-container { grid-template-columns: repeat(auto-fill,minmax(280px,1fr)); }
.card-dashboard { background: var(--card-bg); border-radius:16px; box-shadow:var(--shadow-sm); padding:20px; transition:all 0.3s; }
.card-dashboard:hover { box-shadow:var(--shadow-md); transform:translateY(-2px); }
.card-dashboard .card-title { font-size:1rem; opacity:0.8; margin:0; }
.card-dashboard .card-value { font-size:2rem; font-weight:700; margin:10px 0; }
.chart-card, .card { background: var(--card-bg); border-radius:16px; box-shadow:var(--shadow-sm); padding:20px; }
.chart-card .card-title, .card-header .card-title { font-size:1.25rem; font-weight:600; margin:0; }
.filter-bar { display:flex; gap:16px; background:rgba(0,102,255,0.1); padding:16px; margin-bottom:24px; }
.filter-bar label { display:block; margin-bottom:8px; font-weight:500; }
.filter-bar input, .filter-bar select { width:100%; padding:10px; border-radius:8px; border:1px solid rgba(0,0,0,0.1); }
.table-responsive { overflow-x:auto; }
.data-table { width:100%; border-collapse:collapse; }
.data-table th { background:rgba(0,102,255,0.1); padding:16px; text-align:left; font-weight:600; color:var(--primary); position:sticky; top:0; }
.data-table td { padding:12px 16px; border-bottom:1px solid rgba(0,0,0,0.05); }
.data-table tr:hover { background:rgba(0,102,255,0.1); }
.badge { display:inline-block; padding:4px 12px; border-radius:20px; font-size:0.85rem; font-weight:600; }
.badge-success { background:rgba(0,200,83,0.1); color:var(--status-success); }
.badge-warning { background:rgba(255,171,0,0.1); color:var(--status-warning); }
.badge-danger { background:rgba(255,61,0,0.1); color:var(--status-danger); }
.btn { display:inline-flex; align-items:center; gap:8px; padding:10px 16px; border-radius:12px; font-weight:600; cursor:pointer; transition:0.2s; border:none; }
.btn-primary { background:var(--primary); color:white; }
.btn-accent { background:var(--accent); color:var(--text); }
.btn-outline { background:transparent; border:2px solid var(--primary); color:var(--primary); }
.modal { display:none; position:fixed; z-index:1000; inset:0; background:rgba(0,0,0,0.7); backdrop-filter:blur(5px); }
.modal-content { background:linear-gradient(145deg,#ffffff,#f8faff); margin:5% auto; width:50%; max-width:600px; border-radius:16px; box-shadow:0 10px 30px rgba(0,102,255,0.3); }
.modal-header { background:linear-gradient(90deg,var(--primary),var(--accent)); color:white; padding:16px; display:flex; justify-content:space-between; }
.close-modal { font-size:1.8rem; cursor:pointer; }
.modal-body { padding:24px; }
.form-group { margin-bottom:20px; }
'''  # fim CSS base

# Função gerar módulo completo de Estoque

def criar_modulo_estoque():
    print("\n🚀 Gerando módulo de Estoque com padrão Fisgar Neon Premium...\n")

    # Paths
    mod_dir = os.path.join(BASE_DIR, 'modulos', 'estoque')
    tmpl_dir = os.path.join(BASE_DIR, 'templates', 'estoque')
    css_dir = os.path.join(BASE_DIR, 'static', 'css')
    os.makedirs(mod_dir, exist_ok=True)
    os.makedirs(tmpl_dir, exist_ok=True)
    os.makedirs(css_dir, exist_ok=True)

    # 1) Salvar CSS base
    css_path = os.path.join(css_dir, 'estilo_global.css')
    with open(css_path, 'w', encoding='utf-8') as f:
        f.write(FISGAR_CSS)
    print(f"✅ CSS base gerado: {css_path}")

    # 2) API Flask /api/estoque
    api_code = '''from flask import Blueprint, jsonify
import sqlite3

api_estoque = Blueprint('api_estoque', __name__)

@api_estoque.route('/api/estoque')
def estoque():
    conn = sqlite3.connect('grupo_fisgar.db')
    cur = conn.cursor()
    total = cur.execute("SELECT SUM(quantidade) FROM produtos_processados").fetchone()[0] or 0
    ok = cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade >= 10").fetchone()[0]
    baixo = cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade < 10 AND quantidade > 0").fetchone()[0]
    crit = cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade = 0").fetchone()[0]
    rows = cur.execute("SELECT codigo,nome,fornecedor,quantidade,data_emissao FROM produtos_processados WHERE quantidade <= 10 ORDER BY quantidade ASC").fetchall()
    conn.close()
    detalhe = [{"codigo":r[0],"nome":r[1],"fornecedor":r[2],"estoqueAtual":r[3],"ultimaEntrada":r[4]} for r in rows]
    return jsonify({"totalItens":total,"itensOk":ok,"itensBaixos":baixo,"itensCriticos":crit,"itensCriticosList":detalhe,"entradasMensais":[],"saidasMensais":[],"valoresPorCategoria":[]})'''
    with open(os.path.join(mod_dir, 'api_estoque.py'), 'w', encoding='utf-8') as f:
        f.write(api_code)
    print("✅ API de Estoque gerada em modulos/estoque/api_estoque.py")

    # 3) Template avançado Dashboard
    dashboard_html = '''<!DOCTYPE html>
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
    <div class="page-header">
        <h1 class="page-title">Dashboard</h1>
    </div>
    <div class="cards-container">
        <div class="card-dashboard card-info">
            <div class="card-icon"><i class="bi bi-box-seam"></i></div>
            <h3 class="card-title">Itens no Estoque</h3>
            <p class="card-value" id="totalItens">--</p>
        </div>
        <div class="card-dashboard card-success">
            <div class="card-icon"><i class="bi bi-check-circle"></i></div>
            <h3 class="card-title">Itens OK</h3>
            <p class="card-value" id="itensOk">--</p>
        </div>
        <div class="card-dashboard card-warning">
            <div class="card-icon"><i class="bi bi-exclamation-triangle"></i></div>
            <h3 class="card-title">Itens Baixos</h3>
            <p class="card-value" id="itensBaixos">--</p>
        </div>
        <div class="card-dashboard card-danger">
            <div class="card-icon"><i class="bi bi-x-circle"></i></div>
            <h3 class="card-title">Itens Esgotados</h3>
            <p class="card-value" id="itensCriticos">--</p>
        </div>
    </div>
    <div class="charts-container">
        <div class="chart-card">
            <h3 class="card-title">Movimentação Mensal</h3>
            <canvas id="movimentacaoChart"></canvas>
        </div>
        <div class="chart-card">
            <h3 class="card-title">Categorias (Valor)</h3>
            <canvas id="categoriasChart"></canvas>
        </div>
    </div>
    <div class="card">
        <!-- Tabela dinâmica -->
        <div class="filter-bar">
            <div class="filter-group"><label>Categoria</label><select id="filtro-categoria"><option value="todos">Todos</option></select></div>
            <div class="filter-group"><label>Fornecedor</label><select id="filtro-fornecedor"><option value="todos">Todos</option></select></div>
            <div class="filter-group"><label>Status</label><select id="filtro-status"><option value="todos">Todos</option></select></div>
        </div>
        <div class="card-body table-responsive">
            <table class="data-table" id="tabela-estoque"><thead><tr>
                <th>Código</th><th>Nome</th><th>Fornecedor</th><th>Estoque Atual</th><th>Última Entrada</th><th>Ações</th>
            </tr></thead><tbody></tbody></table>
        </div>
    </div>
</main>
<script>
// Lógica JS para fetch /api/estoque, update cards, charts, tabela, toggle tema
async function loadData() {
    const res = await fetch('/api/estoque'); const data = await res.json();
    document.getElementById('totalItens').textContent = data.totalItens;
    document.getElementById('itensOk').textContent = data.itensOk;
    document.getElementById('itensBaixos').textContent = data.itensBaixos;
    document.getElementById('itensCriticos').textContent = data.itensCriticos;
    // build filter selects
    // fill table tbody
    const tbody = document.querySelector('#tabela-estoque tbody'); tbody.innerHTML='';
    data.itensCriticosList.forEach(i => {
        const tr=document.createElement('tr');
        tr.innerHTML = `
            <td>${i.codigo}</td><td>${i.nome}</td><td>${i.fornecedor}</td><td>${i.estoqueAtual}</td><td>${i.ultimaEntrada}</td>
            <td><button class='btn-outline' onclick="location.href='/estoque/editar/${i.codigo}'">✏️</button></td>`;
        tbody.append(tr);
    });
    // Chart.js init
    const mCtx = document.getElementById('movimentacaoChart');
    new Chart(mCtx, {type:'line',data:{labels:['Jan','Fev','Mar','Abr','Mai','Jun'],datasets:[{label:'Entradas',data:data.entradasMensais,borderColor:'#00c853',fill:true,tension:0.3},{label:'Saídas',data:data.saidasMensais,borderColor:'#0066ff',fill:true,tension:0.3}]},options:{responsive:true}});
    const cCtx = document.getElementById('categoriasChart');
    new Chart(cCtx,{type:'doughnut',data:{labels:['Eletronicos','Materiais','Pecas','Outros'],datasets:[{data:data.valoresPorCategoria,backgroundColor:['#0066ff','#00c853','#ffc107','#ff3d00']}]},options:{responsive:true,plugins:{legend:{position:'right'}}}});
}
function toggleTheme(){document.body.classList.toggle('dark');localStorage.setItem('tema',document.body.classList.contains('dark')?'escuro':'claro');}
window.onload=loadData;
</script>
</body></html>'''
    with open(os.path.join(tmpl_dir, 'dashboard.html'), 'w', encoding='utf-8') as f:
        f.write(dashboard_html)
    print("✅ Dashboard avançado gerado: templates/estoque/dashboard.html")

    # 4) Registrar blueprint automaticamente
    if os.path.exists(APP_PATH):
        content = open(APP_PATH,'r',encoding='utf-8').read()
        if 'api_estoque' not in content:
            lines = content.splitlines()
            for i,l in enumerate(lines):
                if 'Flask' in l:
                    lines.insert(i+1, 'from modulos.estoque.api_estoque import api_estoque')
                    lines.insert(i+2, 'app.register_blueprint(api_estoque)')
                    break
            open(APP_PATH,'w',encoding='utf-8').write('\n'.join(lines))
            print(f"✅ Blueprint API registrado em {APP_PATH}")

# MAIN
if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--tarefa',type=str,help='Comando agente')
    args = parser.parse_args()
    if args.tarefa and 'estoque' in args.tarefa.lower():
        criar_modulo_estoque()
    else:
        print("Use: python agente_fisgar.py --tarefa \"Criar módulo completo de estoque\"")
