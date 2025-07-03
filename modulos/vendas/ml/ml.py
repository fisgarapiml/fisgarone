import sqlite3
from dotenv import load_dotenv, set_key
import os
from datetime import datetime
from flask import Blueprint, render_template, request
from pathlib import Path

# Caminha de onde está o arquivo atual para a raiz que contém o .db
def get_db_path(filename='fisgarone.db'):
    pasta = os.path.abspath(os.path.dirname(__file__))
    while not os.path.exists(os.path.join(pasta, filename)):
        nova_pasta = os.path.dirname(pasta)
        if nova_pasta == pasta:  # chegou na raiz
            raise FileNotFoundError(f"{filename} não encontrado em nenhum diretório acima de {__file__}")
        pasta = nova_pasta
    return os.path.join(pasta, filename)

DB_PATH = get_db_path('fisgarone.db')
ENV_PATH = get_db_path('.env')

print(f"[DEBUG] Usando banco ABSOLUTO: {DB_PATH}")
print(f"[DEBUG] Usando ENV ABSOLUTO: {ENV_PATH}")

ml_bp = Blueprint('ml_bp', __name__)

def inicializar_banco():
    with sqlite3.connect(DB_PATH) as conn:
        ...
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS vendas_ml (
            "ID Pedido" TEXT PRIMARY KEY,
            "Preco Unitario" REAL,
            "Quantidade" INTEGER,
            "Data da Venda" TEXT,
            "Taxa mercado_livre" REAL,
            "Frete" REAL,
            "Conta" TEXT,
            "Cancelamentos" TEXT,
            "Titulo" TEXT,
            "MLB" TEXT,
            "SKU" TEXT,
            "Codigo Envio" TEXT,
            "Comprador" TEXT,
            "Modo Envio" TEXT,
            "Custo Frete Base" REAL,
            "Custo Frete Opcional" REAL,
            "Custo Pedido Frete" REAL,
            "Custo Lista Frete" REAL,
            "Custo Total Frete" REAL,
            "Tipo Logistica" TEXT,
            "Pago Por" TEXT,
            "Situacao" TEXT,
            "Situacao Entrega" TEXT,
            "Data Liberacao" TEXT
        )''')
        conn.commit()

def atualizar_env_token(account_name, new_access_token, new_refresh_token):
    set_key(ENV_PATH, f'ACCESS_TOKEN_{account_name}', new_access_token)
    set_key(ENV_PATH, f'REFRESH_TOKEN_{account_name}', new_refresh_token)


@ml_bp.route('/vendas-ml')
def dashboard_vendas_ml():
    mes = request.args.get('mes')
    status = request.args.get('status')
    conta = request.args.get('conta')
    sku = request.args.get('sku')
    title = request.args.get('title')

    conn = sqlite3.connect(DB_PATH)
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

    # WHERE dinâmico PT-BR
    wheres = ["substr(\"Data da Venda\", 7, 4) || '-' || substr(\"Data da Venda\", 4, 2) = ?"]
    params_atual = [filtro_data_atual]
    params_ant = [filtro_data_ant]

    if status:
        wheres.append("\"Situacao\" = ?")
        params_atual.append(status)
        params_ant.append(status)
    if conta:
        wheres.append("\"Conta\" = ?")
        params_atual.append(conta)
        params_ant.append(conta)
    if sku:
        wheres.append("\"SKU\" = ?")
        params_atual.append(sku)
        params_ant.append(sku)
    if title:
        wheres.append("\"Titulo\" = ?")
        params_atual.append(title)
        params_ant.append(title)

    where_clause = " AND ".join(wheres)

    # FATURAMENTO
    cur.execute(f"""
        SELECT SUM("Preco Unitario" * "Quantidade") as total
        FROM vendas_ml
        WHERE {where_clause}
    """, params_atual)
    faturamento = cur.fetchone()['total'] or 0

    cur.execute(f"""
        SELECT SUM("Preco Unitario" * "Quantidade") as total
        FROM vendas_ml
        WHERE {where_clause}
    """, params_ant)
    faturamento_ant = cur.fetchone()['total'] or 0

    faturamento_var = round(100 * ((faturamento - faturamento_ant) / faturamento_ant), 2) if faturamento_ant else 0

    # UNIDADES
    cur.execute(f"""
        SELECT SUM("Quantidade") as unidades
        FROM vendas_ml
        WHERE {where_clause}
    """, params_atual)
    unidades = cur.fetchone()['unidades'] or 0

    cur.execute(f"""
        SELECT SUM("Quantidade") as unidades
        FROM vendas_ml
        WHERE {where_clause}
    """, params_ant)
    unidades_ant = cur.fetchone()['unidades'] or 0

    unidades_var = round(100 * ((unidades - unidades_ant) / unidades_ant), 2) if unidades_ant else 0

    # PEDIDOS
    cur.execute(f"""
        SELECT COUNT(DISTINCT "ID Pedido") as pedidos
        FROM vendas_ml
        WHERE {where_clause}
    """, params_atual)
    pedidos = cur.fetchone()['pedidos'] or 0

    cur.execute(f"""
        SELECT COUNT(DISTINCT "ID Pedido") as pedidos
        FROM vendas_ml
        WHERE {where_clause}
    """, params_ant)
    pedidos_ant = cur.fetchone()['pedidos'] or 0

    pedidos_var = round(100 * ((pedidos - pedidos_ant) / pedidos_ant), 2) if pedidos_ant else 0

    # TICKET MÉDIO
    ticket_medio = (faturamento / pedidos) if pedidos else 0
    ticket_medio_ant = (faturamento_ant / pedidos_ant) if pedidos_ant else 0
    ticket_var = round(100 * ((ticket_medio - ticket_medio_ant) / ticket_medio_ant), 2) if ticket_medio_ant else 0

    # TOP 10 SKUs
    cur.execute(f"""
        SELECT "SKU", ROUND(SUM("Preco Unitario" * "Quantidade"), 0) AS valor, SUM("Quantidade") AS unidades
        FROM vendas_ml
        WHERE {where_clause}
        GROUP BY "SKU"
        ORDER BY valor DESC
        LIMIT 10
    """, params_atual)
    top10_rows = cur.fetchall()
    top10 = {
        "sku": [row['SKU'] for row in top10_rows],
        "valor": [row['valor'] for row in top10_rows],
        "unidades": [row['unidades'] for row in top10_rows]
    }

    # --- FATURAMENTO DIÁRIO MÊS ATUAL
    cur.execute(f"""
        SELECT substr("Data da Venda", 1, 2) || '/' || substr("Data da Venda", 4, 2) AS dia,
               ROUND(SUM("Preco Unitario" * "Quantidade"), 2) AS faturamento
        FROM vendas_ml
        WHERE substr("Data da Venda", 7, 4) = ? AND substr("Data da Venda", 4, 2) = ?
        GROUP BY dia
        ORDER BY dia
    """, [ano_atual, mes_atual])
    vendas_dia_atual = cur.fetchall()

    from calendar import monthrange

    # Dias do mês atual
    num_dias_atual = monthrange(int(ano_atual), int(mes_atual))[1]
    num_dias_ant = monthrange(int(ano_ant), int(mes_ant))[1]

    # Para alinhar certinho, só até o número de dias existentes em AMBOS os meses
    num_dias_comparar = min(num_dias_atual, num_dias_ant)
    dias = [str(i).zfill(2) for i in range(1, num_dias_comparar + 1)]

    # Faturamento diário mês atual: monta dict só com o dia
    cur.execute(f"""
        SELECT substr("Data da Venda", 1, 2) AS dia,
               ROUND(SUM("Preco Unitario" * "Quantidade"), 2) AS faturamento
        FROM vendas_ml
        WHERE substr("Data da Venda", 7, 4) = ? AND substr("Data da Venda", 4, 2) = ?
        GROUP BY dia
        ORDER BY dia
    """, [ano_atual, mes_atual])
    fat_atual_dict = {row['dia']: row['faturamento'] for row in cur.fetchall()}

    # Faturamento diário mês anterior: monta dict só com o dia
    cur.execute(f"""
        SELECT substr("Data da Venda", 1, 2) AS dia,
               ROUND(SUM("Preco Unitario" * "Quantidade"), 2) AS faturamento
        FROM vendas_ml
        WHERE substr("Data da Venda", 7, 4) = ? AND substr("Data da Venda", 4, 2) = ?
        GROUP BY dia
        ORDER BY dia
    """, [ano_ant, mes_ant])
    fat_ant_dict = {row['dia']: row['faturamento'] for row in cur.fetchall()}

    # Agora SIM os dicionários são do tipo {'01': valor, '02': valor, ...}
    print("DEBUG dias", dias)
    print("DEBUG fat_atual_dict", fat_atual_dict)
    print("DEBUG fat_ant_dict", fat_ant_dict)

    # Agora gera os arrays alinhados pelo dia
    fat_atual = [fat_atual_dict.get(d, 0) for d in dias]
    fat_ant = [fat_ant_dict.get(d, 0) for d in dias]

    # Para o JS, manda os labels no formato correto
    labels = [f"{d}/{mes_atual}" for d in dias]

    vendas_dia = {
        "dia": labels,
        "faturamento": fat_atual,
        "faturamento_ant": fat_ant
    }

    # CAMPOS PARA FILTROS
    cur.execute("SELECT DISTINCT \"Conta\" FROM vendas_ml ORDER BY \"Conta\"")
    contas = [row['Conta'] for row in cur.fetchall() if row['Conta']]

    cur.execute("SELECT DISTINCT \"SKU\" FROM vendas_ml ORDER BY \"SKU\"")
    skus = [row['SKU'] for row in cur.fetchall() if row['SKU']]

    cur.execute("SELECT DISTINCT \"Titulo\" FROM vendas_ml ORDER BY \"Titulo\"")
    titles = [row['Titulo'] for row in cur.fetchall() if row['Titulo']]

    meses = [str(i).zfill(2) for i in range(1, 13)]
    status_options = [('paid', 'Pago'), ('cancelled', 'Cancelado'), ('pending', 'Pendente')]

    conn.close()

    return render_template(
        'vendas/ml/ml_dashboard.html',
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
        status_select=status or '',
        contas=contas,
        conta_select=conta or '',
        skus=skus,
        sku_select=sku or '',
        titles=titles,
        title_select=title or ''
    )



@ml_bp.route('/api/vendas_filtradas')
def vendas_filtradas():
    filtro = request.args.get('filtro')
    conn = sqlite3.connect('fisgarone.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    vendas = []
    titulo = "Vendas"

    # Recupera mês e ano do banco, já em PT-BR
    mes_ano_atual = datetime.now().strftime('%m/%Y')

    if filtro == 'faturamento':
        cur.execute("""
            SELECT * FROM vendas_ml 
            WHERE "Situacao" = 'paid' 
            AND substr("Data da Venda", 4, 7) = ? 
            ORDER BY "Data da Venda" DESC LIMIT 100
        """, (mes_ano_atual,))
        vendas = cur.fetchall()
        titulo = "Vendas Pagas do Mês"
    elif filtro == 'unidades':
        cur.execute("""
            SELECT * FROM vendas_ml 
            WHERE substr("Data da Venda", 4, 7) = ? 
            ORDER BY "Data da Venda" DESC LIMIT 100
        """, (mes_ano_atual,))
        vendas = cur.fetchall()
        titulo = "Unidades Vendidas"
    elif filtro == 'pedidos':
        cur.execute("""
            SELECT * FROM vendas_ml 
            WHERE substr("Data da Venda", 4, 7) = ? 
            ORDER BY "Data da Venda" DESC LIMIT 100
        """, (mes_ano_atual,))
        vendas = cur.fetchall()
        titulo = "Pedidos do Mês"
    elif filtro == 'ticket_medio':
        cur.execute("""
            SELECT * FROM vendas_ml 
            WHERE substr("Data da Venda", 4, 7) = ? 
            ORDER BY "Data da Venda" DESC LIMIT 100
        """, (mes_ano_atual,))
        vendas = cur.fetchall()
        titulo = "Ticket Médio"
    else:
        # Filtro por dia ou SKU PT-BR
        cur.execute("""
            SELECT * FROM vendas_ml 
            WHERE (substr("Data da Venda", 0, 6) = ? OR "SKU" = ?) 
            AND substr("Data da Venda", 4, 7) = ? 
            ORDER BY "Data da Venda" DESC LIMIT 100
        """, (filtro, filtro, mes_ano_atual))
        vendas = cur.fetchall()
        titulo = f"Filtro: {filtro}"
    conn.close()
    return render_template('modais/modal_vendas.html', vendas=vendas, titulo=titulo)

if __name__ == "__main__":
    print("Para usar integração automática com mercado_livre, descomente a linha acima.")
