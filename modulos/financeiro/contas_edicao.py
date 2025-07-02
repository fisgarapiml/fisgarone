from flask import Blueprint, render_template, jsonify, request, current_app
import sqlite3

contas_edicao_bp = Blueprint('contas_edicao', __name__,
                              url_prefix='/financeiro',
                              template_folder='templates/financeiro')

def get_db():
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# 1️⃣ Página da tela
@contas_edicao_bp.route('/contas-edicao')
def pagina_edicao_contas():
    return render_template('contas_edicao.html')

# 2️⃣ API para carregar todos os lançamentos
@contas_edicao_bp.route('/api/contas_a_pagar')
def listar_contas():
    db = get_db()
    contas = db.execute("SELECT * FROM contas_a_pagar ORDER BY vencimento DESC LIMIT 200").fetchall()
    return jsonify([dict(c) for c in contas])

# 3️⃣ API para atualizar uma linha individual
@contas_edicao_bp.route('/api/editar_conta/<int:codigo>', methods=['POST'])
def editar_conta(codigo):
    dados = request.get_json()
    if not dados:
        return jsonify({'success': False, 'error': 'Dados ausentes'})

    campos = ', '.join(f"{k} = ?" for k in dados.keys())
    valores = list(dados.values())
    valores.append(codigo)

    db = get_db()
    db.execute(f"UPDATE contas_a_pagar SET {campos} WHERE codigo = ?", valores)
    db.commit()

    return jsonify({'success': True})

# 4️⃣ API para carregar opções dinâmicas nos selects (empresa, status, etc)
@contas_edicao_bp.route('/api/opcoes_select')
def opcoes_select():
    campo = request.args.get('campo')
    if not campo:
        return jsonify({'error': 'Campo não especificado'}), 400

    db = get_db()
    # Busca valores distintos não nulos para aquele campo
    try:
        resultados = db.execute(
            f'SELECT DISTINCT "{campo}" FROM contas_a_pagar '
            f'WHERE "{campo}" IS NOT NULL '
            f'ORDER BY "{campo}"'
        ).fetchall()
    except sqlite3.OperationalError:
        return jsonify({'error': f'Campo inválido: {campo}'}), 400

    # Retorna só os valores não vazios
    opcoes = [row[0] for row in resultados if row[0] not in (None, '')]
    return jsonify(opcoes)

