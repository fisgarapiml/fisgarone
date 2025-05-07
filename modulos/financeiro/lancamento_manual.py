# novo_arquivo: modulos/financeiro/lancamento_manual.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, jsonify
from werkzeug.utils import secure_filename
import sqlite3
import os
from datetime import datetime

lancamento_manual_bp = Blueprint('lancamento_manual', __name__)

# Caminho absoluto correto para o banco dentro da pasta raiz do projeto
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DB_PATH = os.path.join(ROOT_DIR, 'grupo_fisgar.db')



def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def calcular_status_contas_pagar(vencimento_str, valor_pago):
    try:
        if valor_pago and float(valor_pago) > 0:
            return 'PAGO'
        if not vencimento_str:
            return 'PENDENTE'
        dia, mes, ano = map(int, vencimento_str.split('/'))
        vencimento = datetime(ano, mes, dia).date()
        hoje = datetime.now().date()
        if vencimento < hoje:
            return 'ATRASADO'
        return 'PENDENTE'
    except:
        return 'PENDENTE'

@lancamento_manual_bp.route('/lancamento-manual', methods=['GET', 'POST'])
def lancamento_manual():
    conn = get_db_connection()
    if request.method == 'POST':
        try:
            dados = {
                'vencimento': request.form.get('vencimento'),
                'fornecedor': request.form.get('fornecedor'),
                'banco_pagamento': request.form.get('banco_pagamento'),
                'valor': float(request.form.get('valor', 0)),
                'valor_pago': float(request.form.get('valor_pago', 0)),
                'valor_pendente': float(request.form.get('valor', 0)) - float(request.form.get('valor_pago', 0)),
                'documento': request.form.get('documento'),
                'documento_tipo': request.form.get('tipo_documento'),
                'pagamento_tipo': request.form.get('pagamento_tipo'),
                'plano_de_contas': request.form.get('plano_de_contas'),
                'data_cadastro': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'comentario': request.form.get('comentario'),
                'empresa': request.form.get('empresa'),
                'conta': request.form.get('conta'),
                'status': 'PENDENTE',
                'categorias': request.form.get('categorias'),
                'tipo_custo': request.form.get('tipo_custo'),
                'centro_de_custo': request.form.get('centro_de_custo'),
                'tipo': request.form.get('tipo'),
                'tipo_documento': request.form.get('tipo_documento')
            }

            # Atualizar status e data de pagamento
            dados['status'] = calcular_status_contas_pagar(dados['vencimento'], dados['valor_pago'])
            if dados['status'] == 'PAGO':
                dados['data_pagamento'] = datetime.now().strftime('%Y-%m-%d')

            arquivos = ['arquivo_pagamento', 'arquivo_documento', 'arquivo_xml', 'arquivo_boleto']
            for arquivo in arquivos:
                if arquivo in request.files:
                    file = request.files[arquivo]
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                        os.makedirs(os.path.dirname(filepath), exist_ok=True)
                        file.save(filepath)
                        dados[arquivo] = filename

            colunas = ', '.join(dados.keys())
            placeholders = ', '.join(['?'] * len(dados))
            conn.execute(f"INSERT INTO contas_a_pagar ({colunas}) VALUES ({placeholders})", tuple(dados.values()))
            conn.commit()

            flash('Lançamento registrado com sucesso!', 'success')
            return redirect(url_for('lancamento_manual.lancamento_manual'))

        except Exception as e:
            conn.rollback()
            flash(f'Erro ao registrar lançamento: {str(e)}', 'danger')

    try:
        opcoes = {
            'fornecedores': [row[0] for row in conn.execute("SELECT DISTINCT fornecedor FROM contas_a_pagar WHERE fornecedor IS NOT NULL")],
            'categorias': [row[0] for row in conn.execute("SELECT DISTINCT categorias FROM contas_a_pagar WHERE categorias IS NOT NULL")]
        }
        return render_template('lancamento_manual.html', **opcoes)
    except Exception as e:
        flash(f'Erro ao carregar opções: {str(e)}', 'danger')
        return render_template('lancamento_manual.html')
    finally:
        conn.close()

@lancamento_manual_bp.route('/api/opcoes_select')
def api_opcoes_select():
    campo = request.args.get('campo')
    if not campo:
        return jsonify({'error': 'Campo não especificado'}), 400

    try:
        conn = get_db_connection()
        resultados = conn.execute(
            f'SELECT DISTINCT "{campo}" FROM contas_a_pagar WHERE "{campo}" IS NOT NULL AND "{campo}" != ""'
        ).fetchall()
        opcoes = [row[0] for row in resultados if row[0]]
        return jsonify(opcoes)
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@lancamento_manual_bp.route('/api/resumo_contas')
def api_resumo_contas():
    try:
        conn = get_db_connection()
        pendente = conn.execute(
            "SELECT SUM(valor) FROM contas_a_pagar WHERE status = 'PENDENTE'"
        ).fetchone()[0] or 0
        atrasado = conn.execute(
            "SELECT SUM(valor) FROM contas_a_pagar WHERE status = 'ATRASADO'"
        ).fetchone()[0] or 0
        pago = conn.execute(
            "SELECT SUM(valor_pago) FROM contas_a_pagar WHERE status = 'PAGO' AND data_pagamento >= date('now', '-30 days')"
        ).fetchone()[0] or 0
        total = pendente + atrasado

        return jsonify({
            'pendente': float(pendente),
            'atrasado': float(atrasado),
            'pago': float(pago),
            'total': float(total),
            'variacao_pendente': 0,
            'variacao_atrasado': 0,
            'variacao_pago': 0,
            'variacao_total': 0
        })
    except sqlite3.Error as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
