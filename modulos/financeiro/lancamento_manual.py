from flask import Blueprint, request, jsonify, current_app, render_template
from utils.conexao_postgres import get_db_connection
from datetime import datetime, timedelta

lancamento_manual_bp = Blueprint('lancamento_manual', __name__,
                                 url_prefix='/financeiro/lancamentos',
                                 template_folder='templates')

@lancamento_manual_bp.route('/')
def pagina_lancamento():
    return render_template('lancamento_manual.html')

@lancamento_manual_bp.route('/api/resumo_contas')
def resumo_contas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        mes = request.args.get('mes')
        ano = request.args.get('ano')

        if mes and ano and mes != "undefined" and ano != "undefined":
            mes = str(int(mes)).zfill(2)
            periodo = f"{mes}/{ano}"
            filtro = " AND SUBSTRING(vencimento FROM 4 FOR 7) = %s"
            params = [periodo]
        else:
            filtro = ""
            params = []

        status_map = {
            'pendente': 'Aberto',
            'atrasado': 'Vencido',
            'pago': 'Pago'
        }

        cursor.execute(
            f"SELECT SUM(valor) FROM contas_a_pagar WHERE status = %s{filtro}",
            [status_map['pendente']] + params
        )
        pendente = cursor.fetchone()[0] or 0

        cursor.execute(
            f"SELECT SUM(valor) FROM contas_a_pagar WHERE status = %s{filtro}",
            [status_map['atrasado']] + params
        )
        atrasado = cursor.fetchone()[0] or 0

        cursor.execute(
            f"SELECT SUM(valor_pago) FROM contas_a_pagar WHERE status = %s{filtro}",
            [status_map['pago']] + params
        )
        pago = cursor.fetchone()[0] or 0

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
    finally:
        conn.close()

@lancamento_manual_bp.route('/api/opcoes_select')
def opcoes_select():
    campo = request.args.get('campo')
    if not campo:
        return jsonify({'error': 'Campo não especificado'}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            f'SELECT DISTINCT "{campo}" FROM contas_a_pagar WHERE "{campo}" IS NOT NULL ORDER BY "{campo}"'
        )
        resultados = cursor.fetchall()
        return jsonify([row[0] for row in resultados if row[0]])
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

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

        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO contas_a_pagar 
            (fornecedor, valor, vencimento, status, data_cadastro) 
            VALUES (%s, %s, %s, %s, %s)""",
            tuple(dados.values())
        )
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    finally:
        conn.close()

@lancamento_manual_bp.route('/api/teste')
def teste():
    return jsonify({'status': 'success', 'message': 'Tudo funcionando!'})

@lancamento_manual_bp.route('/api/plano_info')
def plano_info():
    plano = request.args.get('plano')
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fornecedor, categorias, tipo_custo, empresa, conta
            FROM contas_a_pagar
            WHERE plano_de_contas = %s
            ORDER BY data_cadastro DESC
            LIMIT 1
        """, (plano,))
        dados = cursor.fetchone()
        if dados:
            keys = ['fornecedor', 'categorias', 'tipo_custo', 'empresa', 'conta']
            return jsonify(dict(zip(keys, dados)))
        return jsonify({})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
