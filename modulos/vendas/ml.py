import sqlite3
import aiohttp
import asyncio
from dotenv import load_dotenv, set_key
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request

load_dotenv()

ml_bp = Blueprint('ml_bp', __name__)


# ---------------------- BANCO E API ----------------------
def inicializar_banco():
    with sqlite3.connect('grupo_fisgar.db') as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS vendas_ml (
            order_id TEXT PRIMARY KEY,
            unit_price REAL,
            quantity INTEGER,
            date_created TEXT,
            sale_fee REAL,
            shipping_cost REAL,
            seller_id TEXT,
            cancellations TEXT,
            title TEXT,
            mlb TEXT,
            sku TEXT,
            shipment_id TEXT,
            buyer_id TEXT,
            shipping_mode TEXT,
            shipping_base_cost REAL,
            shipping_option_cost REAL,
            shipping_order_cost REAL,
            shipping_list_cost REAL,
            total_shipping_cost REAL,
            logistic_type TEXT,
            paid_by TEXT,
            status TEXT,
            delivery_status TEXT,
            release_date TEXT
        )''')
        conn.commit()


def atualizar_env_token(account_name, new_access_token, new_refresh_token):
    set_key('.env', f'ACCESS_TOKEN_{account_name}', new_access_token)
    set_key('.env', f'REFRESH_TOKEN_{account_name}', new_refresh_token)


# Função para extrair mês de datas no formato ISO com timezone
def extract_month(date_str):
    return date_str[:7]  # Retorna 'YYYY-MM' da string 'YYYY-MM-DDThh:mm:ss.sss-TZ'


# Função para calcular variação percentual segura
def calcular_variacao(atual, anterior):
    if anterior == 0:
        return 100.0 if atual > 0 else 0.0 if atual == 0 else -100.0
    return round(100 * ((atual - anterior) / anterior), 2)


# ---------------------- DASHBOARD VENDAS ML ----------------------
@ml_bp.route('/vendas-ml')
def dashboard_vendas_ml():
    conn = sqlite3.connect('grupo_fisgar.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Obter filtros
    mes_selecionado = request.args.get('mes', '')
    status_selecionado = request.args.get('status', '')
    mes_atual = datetime.now().strftime('%Y-%m')
    mes_anterior = (datetime.now().replace(day=1) - timedelta(days=1)).strftime('%Y-%m')

    # Construir condições WHERE
    def build_where(current_month=True):
        where = []
        params = []

        if mes_selecionado:
            if current_month:
                where.append("SUBSTR(date_created, 6, 2) = ?")
                params.append(mes_selecionado)
            else:
                # Para mês anterior com filtro, precisamos subtrair um mês da data
                where.append(
                    "SUBSTR(date_created, 6, 2) = CAST(? AS INTEGER) - 1 OR SUBSTR(date_created, 6, 2) = '12' AND SUBSTR(date_created, 1, 4) = CAST(? AS INTEGER) - 1")
                params.extend([mes_selecionado, mes_selecionado])
        else:
            if current_month:
                where.append("SUBSTR(date_created, 1, 7) = ?")
                params.append(mes_atual)
            else:
                where.append("SUBSTR(date_created, 1, 7) = ?")
                params.append(mes_anterior)

        if status_selecionado:
            where.append("status = ?")
            params.append(status_selecionado)

        return " AND ".join(["1=1"] + where), params

    # Consultas para o mês atual
    where_current, params_current = build_where(current_month=True)

    # Faturamento atual
    cur.execute(f"SELECT SUM(unit_price*quantity) AS total FROM vendas_ml WHERE {where_current}", params_current)
    faturamento = cur.fetchone()['total'] or 0.0

    # Faturamento anterior
    where_previous, params_previous = build_where(current_month=False)
    cur.execute(f"SELECT SUM(unit_price*quantity) AS total FROM vendas_ml WHERE {where_previous}", params_previous)
    faturamento_ant = cur.fetchone()['total'] or 0.0

    # Unidades vendidas atual
    cur.execute(f"SELECT SUM(quantity) AS unidades FROM vendas_ml WHERE {where_current}", params_current)
    unidades = cur.fetchone()['unidades'] or 0

    # Unidades vendidas anterior
    cur.execute(f"SELECT SUM(quantity) AS unidades FROM vendas_ml WHERE {where_previous}", params_previous)
    unidades_ant = cur.fetchone()['unidades'] or 0

    # Pedidos atual
    cur.execute(f"SELECT COUNT(DISTINCT order_id) AS pedidos FROM vendas_ml WHERE {where_current}", params_current)
    pedidos = cur.fetchone()['pedidos'] or 0

    # Pedidos anterior
    cur.execute(f"SELECT COUNT(DISTINCT order_id) AS pedidos FROM vendas_ml WHERE {where_previous}", params_previous)
    pedidos_ant = cur.fetchone()['pedidos'] or 0

    # Cálculos de variação
    faturamento_var = calcular_variacao(faturamento, faturamento_ant)
    unidades_var = calcular_variacao(unidades, unidades_ant)
    pedidos_var = calcular_variacao(pedidos, pedidos_ant)

    # Ticket médio
    ticket_medio = faturamento / pedidos if pedidos else 0
    ticket_medio_ant = faturamento_ant / pedidos_ant if pedidos_ant else 0
    ticket_var = calcular_variacao(ticket_medio, ticket_medio_ant)

    # Vendas Diárias (formato dia/mês)
    cur.execute(f"""
        SELECT strftime('%d/%m', SUBSTR(date_created, 1, 10)) AS dia, 
               SUM(quantity) AS quantity
        FROM vendas_ml 
        WHERE {where_current}
        GROUP BY dia 
        ORDER BY SUBSTR(date_created, 1, 10)
    """, params_current)
    vendas_dia = cur.fetchall()
    vendas_dia_dict = {
        "dia": [row['dia'] for row in vendas_dia],
        "quantity": [row['quantity'] for row in vendas_dia]
    }

    # Top 10 SKUs
    cur.execute(f"""
        SELECT sku, SUM(quantity) AS quantity 
        FROM vendas_ml
        WHERE {where_current}
        GROUP BY sku 
        ORDER BY quantity DESC 
        LIMIT 10
    """, params_current)
    top10 = cur.fetchall()
    top10_dict = {
        "sku": [row['sku'] for row in top10],
        "quantity": [row['quantity'] for row in top10]
    }

    # Filtros para selects
    meses = [str(i).zfill(2) for i in range(1, 13)]
    status_options = [('paid', 'Pago'), ('cancelled', 'Cancelado'), ('pending', 'Pendente')]

    conn.close()

    return render_template(
        'vendas/vendas_ml_dashboard.html',
        faturamento=faturamento,
        faturamento_ant=faturamento_ant,
        faturamento_var=faturamento_var,
        unidades=unidades,
        unidades_ant=unidades_ant,
        unidades_var=unidades_var,
        pedidos=pedidos,
        pedidos_ant=pedidos_ant,
        pedidos_var=pedidos_var,
        ticket_medio=ticket_medio,
        ticket_medio_ant=ticket_medio_ant,
        ticket_var=ticket_var,
        top10=top10_dict,
        vendas_dia=vendas_dia_dict,
        meses=meses,
        mes_select=mes_selecionado,
        status_options=status_options,
        status_select=status_selecionado
    )


# ---------------------- API MODAL PARA FILTROS DINÂMICOS ----------------------
@ml_bp.route('/api/vendas_filtradas')
def vendas_filtradas():
    filtro = request.args.get('filtro')
    conn = sqlite3.connect('grupo_fisgar.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    vendas = []
    titulo = "Vendas"

    mes_atual = datetime.now().strftime('%Y-%m')

    if filtro == 'faturamento':
        cur.execute("""
            SELECT * FROM vendas_ml 
            WHERE status = 'paid' AND SUBSTR(date_created, 1, 7) = ?
            ORDER BY date_created DESC 
            LIMIT 100
        """, [mes_atual])
        vendas = cur.fetchall()
        titulo = "Vendas Pagas do Mês"
    elif filtro == 'unidades':
        cur.execute("""
            SELECT * FROM vendas_ml 
            WHERE SUBSTR(date_created, 1, 7) = ?
            ORDER BY date_created DESC 
            LIMIT 100
        """, [mes_atual])
        vendas = cur.fetchall()
        titulo = "Unidades Vendidas"
    elif filtro == 'pedidos':
        cur.execute("""
            SELECT * FROM vendas_ml 
            WHERE SUBSTR(date_created, 1, 7) = ?
            ORDER BY date_created DESC 
            LIMIT 100
        """, [mes_atual])
        vendas = cur.fetchall()
        titulo = "Pedidos do Mês"
    elif filtro == 'ticket_medio':
        cur.execute("""
            SELECT * FROM vendas_ml 
            WHERE SUBSTR(date_created, 1, 7) = ?
            ORDER BY date_created DESC 
            LIMIT 100
        """, [mes_atual])
        vendas = cur.fetchall()
        titulo = "Ticket Médio"
    else:
        # Filtro pode ser um dia (ex: "05/06") ou um SKU
        try:
            # Tenta parsear como data
            dia, mes = filtro.split('/')
            cur.execute("""
                SELECT * FROM vendas_ml 
                WHERE SUBSTR(date_created, 9, 2) = ? AND SUBSTR(date_created, 6, 2) = ?
                AND SUBSTR(date_created, 1, 7) = ?
                ORDER BY date_created DESC 
                LIMIT 100
            """, [dia, mes, mes_atual])
            vendas = cur.fetchall()
            titulo = f"Vendas do dia {filtro}"
        except:
            # Se não for data, assume que é SKU
            cur.execute("""
                SELECT * FROM vendas_ml 
                WHERE sku = ? AND SUBSTR(date_created, 1, 7) = ?
                ORDER BY date_created DESC 
                LIMIT 100
            """, [filtro, mes_atual])
            vendas = cur.fetchall()
            titulo = f"Vendas do SKU {filtro}"

    conn.close()
    return render_template('modais/modal_vendas.html', vendas=vendas, titulo=titulo)


# --------- CLI PARA EXECUÇÃO DIRETA ---------
if __name__ == "__main__":
    print("Para usar integração automática com Mercado Livre, implemente a função executar().")