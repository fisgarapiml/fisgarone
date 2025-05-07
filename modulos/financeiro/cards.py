# novo_arquivo: modulos/financeiro/cards.py
from flask import Blueprint, jsonify, current_app
import sqlite3
from datetime import datetime

cards_bp = Blueprint('cards', __name__)

def get_db():
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

@cards_bp.route('/api/cards')
def get_cards():
    db = get_db()
    hoje = datetime.now().strftime('%Y-%m-%d')

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

    db.close()
    return jsonify(dict(dados))
