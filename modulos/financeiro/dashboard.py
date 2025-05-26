from flask import Blueprint, render_template
import sqlite3
import pandas as pd

dashboard = Blueprint('dashboard', __name__, template_folder='../../templates')

# 🔥 CONSULTA DOS PRODUTOS
def consultar_produtos():
    conn = sqlite3.connect('grupo_fisgar.db')
    query = '''
        SELECT 
            nome, 
            unidade_compra, 
            quantidade, 
            valor_total, 
            ipi, 
            fator_conversao, 
            custo_unitario, 
            custo_com_ipi, 
            categorias, 
            status, 
            fornecedor, 
            origem, 
            atualizado_em
        FROM produtos
    '''
    df = pd.read_sql_query(query, conn)
    conn.close()

    df['impacto_no_caixa'] = df['valor_total'].fillna(0) + df['ipi'].fillna(0)
    return df.to_dict(orient='records')


# 🔥 ROTA DO DASHBOARD
@dashboard.route('/dashboard_financeiro')
def dashboard_financeiro():
    produtos = consultar_produtos()

    total_estoque = sum([p.get('quantidade', 0) or 0 for p in produtos])
    total_valor_estoque = sum([p.get('valor_total', 0) or 0 for p in produtos])
    total_ipi = sum([p.get('ipi', 0) or 0 for p in produtos])
    saldo_total = total_valor_estoque + total_ipi

    return render_template('dashboard_financeiro.html',
                           produtos=produtos,
                           total_estoque=total_estoque,
                           total_valor_estoque=total_valor_estoque,
                           total_ipi=total_ipi,
                           saldo_total=saldo_total)
