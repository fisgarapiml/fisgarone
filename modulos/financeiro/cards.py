# modulos/financeiro/cards.py
from flask import Blueprint, jsonify, current_app, url_for
import sqlite3
from datetime import datetime

# Criação do blueprint com nome padrão
cards_bp = Blueprint('cards_bp', __name__)


def get_db():
    """Obtém conexão com o banco de dados"""
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


@cards_bp.route('/')
def get_cards():
    """Endpoint principal que retorna os dados dos cards financeiros"""
    db = get_db()
    hoje = datetime.now().strftime('%Y-%m-%d')

    try:
        dados = db.execute('''
            SELECT 
                SUM(CASE WHEN status != "pago" THEN valor ELSE 0 END) as previsto,
                SUM(CASE WHEN status = "pago" THEN valor ELSE 0 END) as pago,
                SUM(CASE WHEN status != "pago" THEN valor ELSE 0 END) - 
                SUM(CASE WHEN status = "pago" THEN valor ELSE 0 END) as saldo,
                COUNT(CASE WHEN data_vencimento = ? AND status != "pago" THEN 1 END) as hoje,
                COUNT(CASE WHEN data_vencimento < ? AND status != "pago" THEN 1 END) as atrasados
            FROM lancamento_contas_pagar
        ''', (hoje, hoje)).fetchone()

        return jsonify({
            'previsto': dados['previsto'] or 0,
            'pago': dados['pago'] or 0,
            'saldo': dados['saldo'] or 0,
            'vencimentos_hoje': dados['hoje'] or 0,
            'atrasados': dados['atrasados'] or 0,
            'status': 'success'
        })

    except Exception as e:
        current_app.logger.error(f"Erro ao buscar cards: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': 'Erro ao processar dados financeiros'
        }), 500

    finally:
        db.close()


# Exemplo de uso do url_for dentro do mesmo arquivo
def get_cards_url():
    """Exemplo de como usar url_for dentro do módulo"""
    return url_for('cards_bp.get_cards')