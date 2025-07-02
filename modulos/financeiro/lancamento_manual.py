from flask import Blueprint, request, jsonify, current_app, render_template
import sqlite3
import os
from datetime import datetime, timedelta

# 1. Blueprint com configuração completa
lancamento_manual_bp = Blueprint('financeiro/lancamento_manual', __name__,
                                 url_prefix='/financeiro/lancamentos',
                                 template_folder='templates')


# 2. Conexão com o banco (igual ao seu app central)
def get_db():
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


# 3. Rota PRINCIPAL para a página HTML (adicionada agora)
@lancamento_manual_bp.route('/')
def lancamento():
    return render_template('financeiro/lancamento_manual.html')


# 4. API para os cards (mantida igual ao seu frontend)
@lancamento_manual_bp.route('/api/resumo_contas')
def resumo_contas():
    try:
        db = get_db()

        # Consultas otimizadas
        pendente = db.execute("SELECT SUM(valor) FROM contas_a_pagar WHERE status = 'PENDENTE'").fetchone()[0] or 0
        atrasado = db.execute("SELECT SUM(valor) FROM contas_a_pagar WHERE status = 'ATRASADO'").fetchone()[0] or 0
        pago = db.execute("SELECT SUM(valor_pago) FROM contas_a_pagar WHERE status = 'PAGO'").fetchone()[0] or 0

        return jsonify({
            'pendente': float(pendente),
            'atrasado': float(atrasado),
            'pago': float(pago),
            'total': float(pendente) + float(atrasado),
            'variacao_pendente': 0,
            'variacao_atrasado': 0,
            'variacao_pago': 0,
            'variacao_total': 0
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 5. API para os selects dinâmicos
@lancamento_manual_bp.route('/api/opcoes_select')
def opcoes_select():
    campo = request.args.get('campo')
    if not campo:
        return jsonify({'error': 'Campo não especificado'}), 400

    try:
        db = get_db()
        resultados = db.execute(
            f'SELECT DISTINCT "{campo}" FROM contas_a_pagar WHERE "{campo}" IS NOT NULL ORDER BY "{campo}"'
        ).fetchall()
        return jsonify([row[0] for row in resultados if row[0]])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# 6. API para salvar lançamentos (com tratamento de parcelas)
@lancamento_manual_bp.route('/api/salvar_lancamento', methods=['POST'])
def salvar_lancamento():
    try:
        dados = {
            'fornecedor': request.form.get('fornecedor'),
            'valor': float(request.form.get('valor', 0)),
            'vencimento': request.form.get('vencimento'),
            # ... (adicione todos os campos do seu formulário)
            'status': 'PENDENTE',
            'data_cadastro': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

        db = get_db()
        db.execute(
            """INSERT INTO contas_a_pagar 
            (fornecedor, valor, vencimento, status, data_cadastro) 
            VALUES (?, ?, ?, ?, ?)""",
            tuple(dados.values())
        )
        db.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# 7. Rota de teste (opcional)
@lancamento_manual_bp.route('/api/teste')
def teste():
    return jsonify({'status': 'success', 'message': 'Tudo funcionando!'})

@lancamento_manual_bp.route('/api/plano_info')
def plano_info():
    plano = request.args.get('plano')  # variável correta
    db = get_db()

    dados = db.execute("""
        SELECT fornecedor, categorias, tipo_custo, empresa, conta
        FROM contas_a_pagar
        WHERE plano_de_contas = ?
        ORDER BY data_cadastro DESC
        LIMIT 1
    """, (plano,)).fetchone()

    if dados:
        return jsonify(dict(dados))
    return jsonify({})
