import sqlite3
from flask import Blueprint, render_template, jsonify, request
from datetime import datetime
import math

estoque_bp = Blueprint('estoque', __name__, template_folder='templates')


def get_db_connection():
    conn = sqlite3.connect('grupo_fisgar.db')
    conn.row_factory = sqlite3.Row
    return conn


@estoque_bp.route('/dashboard')
def dashboard():
    conn = get_db_connection()

    # Dados para os cards
    cards_data = {
        'total_itens': conn.execute('SELECT COUNT(*) FROM estoque').fetchone()[0],
        'itens_ok': conn.execute('SELECT COUNT(*) FROM estoque WHERE qtd_estoque > estoque_minimo * 1.2').fetchone()[0],
        'itens_baixos': conn.execute(
            'SELECT COUNT(*) FROM estoque WHERE qtd_estoque <= estoque_minimo * 1.2 AND qtd_estoque > 0').fetchone()[0],
        'itens_esgotados': conn.execute('SELECT COUNT(*) FROM estoque WHERE qtd_estoque = 0').fetchone()[0]
    }

    # Itens críticos
    itens_criticos = conn.execute('''
        SELECT * FROM estoque 
        WHERE qtd_estoque <= estoque_minimo OR qtd_estoque = 0
        ORDER BY qtd_estoque ASC
    ''').fetchall()

    # Dados para gráficos
    meses = ['Jan', 'Fev', 'Mar', 'Abr', 'Mai', 'Jun']
    entradas = [math.floor(100 + i * 30 + (i * 20 * math.sin(i))) for i in range(6)]
    saidas = [math.floor(80 + i * 25 + (i * 15 * math.cos(i))) for i in range(6)]

    categorias = ['Eletrônicos', 'Roupas', 'Alimentos', 'Móveis', 'Outros']
    valores = [12000, 8500, 6300, 4200, 3100]

    conn.close()

    return render_template('estoque/dashboard.html',
                           cards_data=cards_data,
                           itens_criticos=itens_criticos,
                           meses=meses,
                           entradas=entradas,
                           saidas=saidas,
                           categorias=categorias,
                           valores=valores)


@estoque_bp.route('/api/itens/<tipo>')
def api_itens(tipo):
    conn = get_db_connection()

    if tipo == 'todos':
        itens = conn.execute('SELECT * FROM estoque ORDER BY nome').fetchall()
    elif tipo == 'ok':
        itens = conn.execute('SELECT * FROM estoque WHERE qtd_estoque > estoque_minimo * 1.2').fetchall()
    elif tipo == 'baixa':
        itens = conn.execute(
            'SELECT * FROM estoque WHERE qtd_estoque <= estoque_minimo * 1.2 AND qtd_estoque > 0').fetchall()
    elif tipo == 'esgotados':
        itens = conn.execute('SELECT * FROM estoque WHERE qtd_estoque = 0').fetchall()
    else:
        itens = []

    conn.close()
    return jsonify([dict(item) for item in itens])


@estoque_bp.route('/api/atualizar', methods=['POST'])
def atualizar_item():
    data = request.get_json()
    conn = get_db_connection()

    try:
        conn.execute('''
            UPDATE estoque 
            SET qtd_estoque = ?, estoque_minimo = ?, estoque_maximo = ?, 
                preco_venda = ?, data_atualizacao = datetime('now','localtime')
            WHERE id = ?
        ''', (data['qtd_estoque'], data['estoque_minimo'], data['estoque_maximo'],
              data['preco_venda'], data['id']))
        conn.commit()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
    finally:
        conn.close()

        @estoque_bp.route('/api/itens/criticos')
        def itens_criticos():
            conn = get_db_connection()
            itens = conn.execute('''
                SELECT * FROM estoque 
                WHERE qtd_estoque <= estoque_minimo 
                ORDER BY qtd_estoque / estoque_minimo ASC
                LIMIT 10
            ''').fetchall()
            conn.close()
            return jsonify([dict(item) for item in itens])

        @estoque_bp.route('/api/itens/vencimento')
        def itens_proximo_vencimento():
            conn = get_db_connection()
            itens = conn.execute('''
                SELECT * FROM estoque
                WHERE data_validade IS NOT NULL
                ORDER BY julianday(data_validade) - julianday('now')
                LIMIT 10
            ''').fetchall()
            conn.close()
            return jsonify([dict(item) for item in itens])

        @estoque_bp.route('/api/itens/lentagem')
        def itens_baixa_rotacao():
            conn = get_db_connection()
            itens = conn.execute('''
                SELECT e.*, 
                       (SELECT COUNT(*) FROM movimentacao 
                        WHERE produto_id = e.id AND strftime('%m', data) = strftime('%m', 'now')) as mov_mes
                FROM estoque e
                ORDER BY mov_mes ASC
                LIMIT 10
            ''').fetchall()
            conn.close()
            return jsonify([dict(item) for item in itens])