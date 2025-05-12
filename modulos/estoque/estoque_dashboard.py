# novo_arquivo: modulos/estoque/estoque_dashboard.py
from flask import Blueprint, render_template, current_app
import sqlite3
import json

estoque_bp = Blueprint('estoque_bp', __name__)

def get_db_connection():
    conn = sqlite3.connect(current_app.config['DATABASE'])  # ← Respeita a configuração central
    conn.row_factory = sqlite3.Row
    return conn

@estoque_bp.route('/estoque')
def estoque_dashboard():
    conn = get_db_connection()
    try:
        cursor = conn.cursor()

        # Dados para os cards principais
        cursor.execute('''
            SELECT 
                COUNT(*) as total_itens,
                SUM(CASE WHEN estoque_atual > estoque_minimo THEN 1 ELSE 0 END) as itens_ok,
                SUM(CASE WHEN estoque_atual > 0 AND estoque_atual <= estoque_minimo THEN 1 ELSE 0 END) as itens_baixos,
                SUM(CASE WHEN estoque_atual = 0 THEN 1 ELSE 0 END) as itens_esgotados
            FROM produtos
        ''')
        cards_data = cursor.fetchone()

        # Itens críticos (abaixo do mínimo)
        cursor.execute('''
            SELECT p.codigo, p.nome, p.categoria, f.nome as fornecedor, 
                   p.estoque_atual, p.estoque_minimo,
                   CASE 
                       WHEN p.estoque_atual = 0 THEN 'Esgotado'
                       WHEN p.estoque_atual <= p.estoque_minimo THEN 'Crítico'
                       ELSE 'OK'
                   END as status,
                   (SELECT MAX(data) FROM movimentacoes WHERE produto_id = p.id AND tipo = 'entrada') as ultima_entrada
            FROM produtos p
            LEFT JOIN fornecedores f ON p.fornecedor_id = f.id
            WHERE p.estoque_atual <= p.estoque_minimo
            ORDER BY p.estoque_atual ASC
            LIMIT 50
        ''')
        itens_criticos = [dict(row) for row in cursor.fetchall()]

        # Dados fictícios para os gráficos (substituir por dados reais depois)
        meses = ['Jan', 'Fev', 'Mar']
        entradas = [120, 190, 170]
        saidas = [80, 120, 140]
        categorias = ['Brinquedos', 'Doces']
        valores = [8200, 4200]

        return render_template('estoque.html',
                               cards_data=cards_data,
                               itens_criticos=itens_criticos,
                               meses=json.dumps(meses),
                               entradas=json.dumps(entradas),
                               saidas=json.dumps(saidas),
                               categorias=json.dumps(categorias),
                               valores=json.dumps(valores))
    except Exception as e:
        print(f"Erro na rota estoque: {str(e)}")
        return render_template('estoque.html',
                               cards_data={},
                               itens_criticos=[],
                               meses=json.dumps([]),
                               entradas=json.dumps([]),
                               saidas=json.dumps([]),
                               categorias=json.dumps([]),
                               valores=json.dumps([]))
    finally:
        conn.close()
