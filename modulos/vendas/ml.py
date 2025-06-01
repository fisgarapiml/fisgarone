import sqlite3
import aiohttp
import asyncio
from dotenv import load_dotenv, set_key
import os
from datetime import datetime
from flask import Blueprint, render_template, request

load_dotenv()

ml_bp = Blueprint('ml_bp', __name__)

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

@ml_bp.route('/vendas-ml')
def dashboard_vendas_ml():
    mes = request.args.get('mes')
    status = request.args.get('status')

    conn = sqlite3.connect('grupo_fisgar.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    now = datetime.now()
    mes_atual = mes or now.strftime('%m')
    ano_atual = now.strftime('%Y')

    if int(mes_atual) == 1:
        mes_ant = '12'
        ano_ant = str(int(ano_atual) - 1)
    else:
        mes_ant = str(int(mes_atual) - 1).zfill(2)
        ano_ant = ano_atual

    filtro_data_atual = f"{ano_atual}-{mes_atual}"
    filtro_data_ant = f"{ano_ant}-{mes_ant}"

    where_status = ""
    params = []
    if status:
        where_status = "AND status = ?"
        params.append(status)

    # FATURAMENTO
    cur.execute(f"""
        SELECT SUM(unit_price * quantity) as total
        FROM vendas_ml
        WHERE substr(date_created, 1, 7) = ? {where_status}
    """, [filtro_data_atual] + params)
    faturamento = cur.fetchone()['total'] or 0

    cur.execute(f"""
        SELECT SUM(unit_price * quantity) as total
        FROM vendas_ml
        WHERE substr(date_created, 1, 7) = ? {where_status}
    """, [filtro_data_ant] + params)
    faturamento_ant = cur.fetchone()['total'] or 0

    faturamento_var = round(100 * ((faturamento - faturamento_ant) / faturamento_ant), 2) if faturamento_ant else 0

    # UNIDADES
    cur.execute(f"""
        SELECT SUM(quantity) as unidades
        FROM vendas_ml
        WHERE substr(date_created, 1, 7) = ? {where_status}
    """, [filtro_data_atual] + params)
    unidades = cur.fetchone()['unidades'] or 0

    cur.execute(f"""
        SELECT SUM(quantity) as unidades
        FROM vendas_ml
        WHERE substr(date_created, 1, 7) = ? {where_status}
    """, [filtro_data_ant] + params)
    unidades_ant = cur.fetchone()['unidades'] or 0

    unidades_var = round(100 * ((unidades - unidades_ant) / unidades_ant), 2) if unidades_ant else 0

    # PEDIDOS
    cur.execute(f"""
        SELECT COUNT(DISTINCT order_id) as pedidos
        FROM vendas_ml
        WHERE substr(date_created, 1, 7) = ? {where_status}
    """, [filtro_data_atual] + params)
    pedidos = cur.fetchone()['pedidos'] or 0

    cur.execute(f"""
        SELECT COUNT(DISTINCT order_id) as pedidos
        FROM vendas_ml
        WHERE substr(date_created, 1, 7) = ? {where_status}
    """, [filtro_data_ant] + params)
    pedidos_ant = cur.fetchone()['pedidos'] or 0

    pedidos_var = round(100 * ((pedidos - pedidos_ant) / pedidos_ant), 2) if pedidos_ant else 0

    # TICKET MÉDIO
    ticket_medio = (faturamento / pedidos) if pedidos else 0
    ticket_medio_ant = (faturamento_ant / pedidos_ant) if pedidos_ant else 0
    ticket_var = round(100 * ((ticket_medio - ticket_medio_ant) / ticket_medio_ant), 2) if ticket_medio_ant else 0

    # TOP 10 SKUs
    cur.execute(f"""
        SELECT sku, SUM(quantity) AS quantity
        FROM vendas_ml
        WHERE substr(date_created, 1, 7) = ? {where_status}
        GROUP BY sku
        ORDER BY quantity DESC
        LIMIT 10
    """, [filtro_data_atual] + params)
    top10_rows = cur.fetchall()
    top10 = {
        "sku": [row['sku'] for row in top10_rows],
        "quantity": [row['quantity'] for row in top10_rows]
    }


    # VENDAS DIÁRIAS (agora faturamento por dia, não unidades)
    cur.execute(f"""
        SELECT strftime('%d/%m', substr(date_created, 1, 10)) AS dia,
               ROUND(SUM(unit_price * quantity), 2) AS faturamento
        FROM vendas_ml
        WHERE substr(date_created, 1, 7) = ? {where_status}
        GROUP BY dia
        ORDER BY dia
    """, [filtro_data_atual] + params)
    vendas_dia_rows = cur.fetchall()
    vendas_dia = {
        "dia": [row['dia'] for row in vendas_dia_rows],
        "faturamento": [row['faturamento'] for row in vendas_dia_rows]
    }

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
        top10=top10,
        vendas_dia=vendas_dia,
        meses=meses,
        mes_select=mes_atual,
        status_options=status_options,
        status_select=status or ''
    )

@ml_bp.route('/api/vendas_filtradas')
def vendas_filtradas():
    filtro = request.args.get('filtro')
    conn = sqlite3.connect('grupo_fisgar.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    vendas = []
    titulo = "Vendas"

    mes_atual = cur.execute("SELECT strftime('%Y-%m', 'now', '-3 hours')").fetchone()[0]

    if filtro == 'faturamento':
        cur.execute("SELECT * FROM vendas_ml WHERE status = 'paid' AND substr(date_created, 1, 7) = ? ORDER BY date_created DESC LIMIT 100", (mes_atual,))
        vendas = cur.fetchall()
        titulo = "Vendas Pagas do Mês"
    elif filtro == 'unidades':
        cur.execute("SELECT * FROM vendas_ml WHERE substr(date_created, 1, 7) = ? ORDER BY date_created DESC LIMIT 100", (mes_atual,))
        vendas = cur.fetchall()
        titulo = "Unidades Vendidas"
    elif filtro == 'pedidos':
        cur.execute("SELECT * FROM vendas_ml WHERE substr(date_created, 1, 7) = ? ORDER BY date_created DESC LIMIT 100", (mes_atual,))
        vendas = cur.fetchall()
        titulo = "Pedidos do Mês"
    elif filtro == 'ticket_medio':
        cur.execute("SELECT * FROM vendas_ml WHERE substr(date_created, 1, 7) = ? ORDER BY date_created DESC LIMIT 100", (mes_atual,))
        vendas = cur.fetchall()
        titulo = "Ticket Médio"
    else:
        cur.execute("""
            SELECT * FROM vendas_ml 
            WHERE (strftime('%d/%m', substr(date_created, 1, 10)) = ? OR sku = ?) 
            AND substr(date_created, 1, 7) = ? 
            ORDER BY date_created DESC LIMIT 100
            """, (filtro, filtro, mes_atual))
        vendas = cur.fetchall()
        titulo = f"Filtro: {filtro}"
    conn.close()
    return render_template('modais/modal_vendas.html', vendas=vendas, titulo=titulo)

if __name__ == "__main__":
    # asyncio.run(executar())  # Descomente se usar integração automática ML
    print("Para usar integração automática com Mercado Livre, descomente a linha acima.")
