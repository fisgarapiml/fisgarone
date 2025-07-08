# === PROCESSAMENTO AUTOMATIZADO MERCADO LIVRE ===
# COMPLETO: Busca, traduz, migra, calcula. NADA OMITIDO.
import sqlite3
import aiohttp
import asyncio
from dotenv import load_dotenv, set_key
import os
from datetime import datetime, timedelta
from dateutil import parser
import pytz
from flask import Blueprint
from dotenv import load_dotenv
from pathlib import Path
import random
import time
import pandas as pd


# Caminho absoluto para raiz do projeto (ajuste se o seu não for C:/fisgarone/)
DB_PATH = "C:/fisgarone/fisgarone.db"
ENV_PATH = "C:/fisgarone/.env"

load_dotenv(dotenv_path=ENV_PATH, override=True)

importador_automatico_bp = Blueprint('importador_automatico_bp', __name__)


# --- SUA FUNÇÃO DE TRADUÇÃO (não altera nada) ---
def traduzir_valores(coluna, valor):
    if valor is None:
        return valor
    valor = str(valor).lower()
    if coluna == "Tipo Logistica":
        if "fulfillment" in valor:
            return "Full"
        elif "xd_drop_off" in valor:
            return "Ponto de Coleta"
        elif "self_service" in valor:
            return "Flex"
    elif coluna == "Situacao":
        if "ready_to_ship" in valor:
            return "Pronto para Envio"
        elif "shipped" in valor:
            return "Enviado"
        elif "cancelled" in valor:
            return "Cancelado"
        elif "pending" in valor:
            return "Pendente"
        elif "delivered" in valor:
            return "Entregue"
    elif coluna == "Conta":
        if "202989490" in valor:
            return "Comercial"
        elif "702704896" in valor:
            return "Camping"
        elif "263678949" in valor:
            return "Pesca"
        elif "555536943" in valor:
            return "Toys"
    return valor


# --- SUA FUNÇÃO DE INICIALIZAÇÃO ---
def inicializar_banco():
    print(f"Inicializando o banco de dados em: {DB_PATH}")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS vendas_ml (
            "ID Pedido" TEXT PRIMARY KEY,
            "Preco Unitario" REAL,
            "Quantidade" INTEGER,
            "Data da Venda" TEXT,
            "Taxa Mercado Livre" REAL,
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
            "Data Liberacao" TEXT,
            "Taxa Fixa ML" REAL,
            "Comissoes" REAL,
            "Comissao (%)" REAL
        )''')
        # Tabela repasses_ml: cria se não existe, sem perder dados existentes!
        cursor.execute('''CREATE TABLE IF NOT EXISTS repasses_ml (
            "ID Pedido" TEXT PRIMARY KEY,
            "Data da Venda" TEXT,
            "Conta" TEXT,
            "Preco Unitario" REAL,
            "Quantidade" INTEGER,
            "Taxa Fixa ML" REAL,
            "Comissoes" REAL,
            "Frete Seller" REAL,
            "Total da Venda" REAL,
            "Total Custo" REAL,
            "Valor do Repasse" REAL,
            "Data Liberacao" TEXT
        )''')
        # Tabela entradas_financeiras (garantir que existe)
        cursor.execute('''CREATE TABLE IF NOT EXISTS entradas_financeiras (
            "id" INTEGER PRIMARY KEY AUTOINCREMENT,
            "tipo" TEXT,
            "pedido_id" TEXT,
            "data_venda" TEXT,
            "data_liberacao" TEXT,
            "valor_total" REAL,
            "valor_liquido" REAL,
            "comissoes" REAL,
            "taxas" REAL,
            "frete" REAL,
            "status" TEXT,
            "origem_conta" TEXT,
            UNIQUE(pedido_id, tipo)
        )''')
        conn.commit()


from dotenv import set_key


def atualizar_env_token(account_name, new_access_token, new_refresh_token):
    set_key(ENV_PATH, f'ACCESS_TOKEN_{account_name}', new_access_token)
    set_key(ENV_PATH, f'REFRESH_TOKEN_{account_name}', new_refresh_token)


# === FUNÇÕES DE BUSCA/API COM MELHORIAS PARA TRATAR ERRO 403 ===
async def fetch_with_retry(session, url, headers, max_retries=0):
    for attempt in range(max_retries):
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 403:
                    print(f"Erro 403 (Acesso Negado) na tentativa {attempt + 1} para {url}")
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 1  # Backoff exponencial
                        print(f"Aguardando {wait_time} segundos antes de tentar novamente...")
                        await asyncio.sleep(wait_time)
                        continue
                    else:
                        print(f"Falha após {max_retries} tentativas para {url}")
                        return None
                elif response.status == 429:
                    wait_time = random.uniform(1, 0)
                    print(f"Rate limit atingido. Tentativa {attempt + 1}. Aguardando {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"Erro {response.status} em {url}: {await response.text()}")
                    return None
        except Exception as e:
            print(f"Erro na tentativa {attempt + 1} para {url}: {str(e)}")
            if attempt == max_retries - 1:
                return None
            await asyncio.sleep(1)
    return None


async def refresh_token(client_id, client_secret, refresh_token, api_url, session):
    url = f"{api_url}/oauth/token"
    data = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token
    }
    try:
        async with session.post(url, data=data) as response:
            if response.status == 200:
                new_tokens = await response.json()
                return new_tokens.get('access_token'), new_tokens.get('refresh_token')
            else:
                print(
                    f"Erro ao atualizar o token para o client_id {client_id}: {response.status} - {await response.text()}")
                return None, None
    except Exception as e:
        print(f"Erro ao tentar atualizar o token: {e}")
        return None, None


async def fetch_shipment_costs_and_payments(access_token, shipment_id, api_url, session):
    headers = {"Authorization": f"Bearer {access_token}", "x-format-new": "true"}
    costs_url = f"{api_url}/shipments/{shipment_id}/costs"
    payments_url = f"{api_url}/shipments/{shipment_id}/payments"

    try:
        # Adicionando retentativa para custos
        costs_data = await fetch_with_retry(session, costs_url, headers)
        if costs_data:
            shipping_base_cost = float(costs_data.get("gross_amount", 0.0))
        else:
            print(f"Erro ao buscar custos do envio para {shipment_id}")
            return None, None

        # Adicionando retentativa para pagamentos
        payments_data = await fetch_with_retry(session, payments_url, headers)
        if payments_data:
            if isinstance(payments_data, list) and payments_data:
                shipping_cost = float(payments_data[0].get("amount", 0.0))
            elif isinstance(payments_data, dict):
                shipping_cost = float(payments_data.get("amount", 0.0))
            else:
                shipping_cost = 0.0
        else:
            print(f"Erro ao buscar pagamentos do envio para {shipment_id}")
            return None, None

        return shipping_cost, shipping_base_cost
    except Exception as e:
        print(f"Erro ao acessar dados de envio e pagamentos: {e}")
        return None, None


async def fetch_billing_details(access_token, order_id, api_url, session):
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    url = f"{api_url}/billing/integration/group/ML/order/details?order_ids={order_id}"

    data = await fetch_with_retry(session, url, headers)
    if not data or not data.get('results'):
        print(f"Nenhum dado de billing encontrado para o pedido {order_id}")
        return None

    order_data = data['results'][0]
    paid_by = "seller"

    # Verifica quem pagou o frete
    for detail in order_data.get('details', []):
        shipping_info = detail.get('shipping_info', {})
        if shipping_info and float(shipping_info.get('receiver_shipping_cost', 1)) > 0:
            paid_by = "buyer"
            break

    # Obtém data de liberação
    release_date = None
    payment_info = order_data.get('payment_info', [{}])[0]
    if payment_info and 'money_release_date' in payment_info:
        try:
            release_date = parser.parse(payment_info['money_release_date']).strftime("%Y-%m-%d %H:%M:%S")
        except:
            pass

    return {
        "paid_by": paid_by,
        "release_date": release_date
    }


async def fetch_shipment(access_token, shipment_id, api_url, session):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{api_url}/shipments/{shipment_id}"

    shipment = await fetch_with_retry(session, url, headers)
    if not shipment:
        return None

    logistic_type = shipment.get("logistic_type", "Não disponível")
    shipping_mode = shipment.get("shipping_mode", "")
    shipping_base_cost = float(shipment.get("shipping_option", {}).get("base_cost", 0.0))
    shipping_option_cost = float(shipment.get("shipping_option", {}).get("cost", 0.0))
    shipping_order_cost = float(shipment.get("order_cost", 0.0))
    shipping_list_cost = float(shipment.get("shipping_option", {}).get("list_cost", 0.0))
    total_shipping_cost = float(shipment.get("total", 0.0))
    status = shipment.get("status", "")
    delivery_status = shipment.get("tracking", {}).get("status", "")
    release_date = shipment.get("date_estimated_delivery", {}).get("date", None)

    if release_date:
        try:
            release_date = datetime.strptime(release_date, "%Y-%m-%dT%H:%M:%S")
            release_date = release_date.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            release_date = None

    date_created = shipment.get("date_created", "")
    if date_created:
        try:
            dt_obj = parser.parse(date_created)
            date_created_br = dt_obj.strftime("%d/%m/%Y")
        except Exception:
            date_created_br = date_created
    else:
        date_created_br = ""

    shipping_cost, shipping_base_cost = await fetch_shipment_costs_and_payments(
        access_token, shipment_id, api_url, session
    )

    if shipping_cost is not None and shipping_base_cost is not None:
        total_shipping_cost = shipping_cost
        return {
            "logistic_type": logistic_type,
            "shipping_mode": shipping_mode,
            "shipping_base_cost": shipping_base_cost,
            "shipping_option_cost": shipping_option_cost,
            "shipping_order_cost": shipping_order_cost,
            "shipping_list_cost": shipping_list_cost,
            "total_shipping_cost": total_shipping_cost,
            "status": status,
            "delivery_status": delivery_status,
            "release_date": release_date,
            "date_created": date_created
        }
    return None


async def buscar_pedidos_e_envios(access_token, seller_id, api_url, session):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        headers = {"Authorization": f"Bearer {access_token}"}
        offset = 0
        limit = 50
        total = 0
        data_60_dias_antes = datetime.now(pytz.timezone('America/Sao_Paulo')) - timedelta(days=60)
        data_60_dias_antes_str = data_60_dias_antes.strftime("%Y-%m-%dT%H:%M:%S%z")
        print(f"Buscando pedidos a partir de: {data_60_dias_antes_str}")
        print(f"Iniciando a busca de pedidos para o seller_id: {seller_id}")

        while offset < total or total == 0:
            url_pedidos = f"{api_url}/orders/search?seller={seller_id}&date_created.from={data_60_dias_antes_str}&offset={offset}&limit={limit}"
            print(f"API ML] {url_pedidos}")

            try:
                async with session.get(url_pedidos, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        pedidos = data.get('results', [])
                        total = data.get('paging', {}).get('total', 0)

                        if total == 0:
                            print(f"Nenhum pedido encontrado para o Seller ID {seller_id}.")
                        else:
                            print(f"Total de pedidos encontrados para o Seller ID {seller_id}: {total}")

                            for pedido in pedidos:
                                order_id = pedido.get("id", "")
                                date_created = pedido.get("date_created", "")

                                if date_created:
                                    try:
                                        date_created_obj = parser.parse(date_created)
                                        date_created_br = date_created_obj.strftime("%d/%m/%Y")
                                    except Exception:
                                        date_created_br = date_created
                                else:
                                    date_created_br = ""

                                try:
                                    if date_created:
                                        date_created_obj = parser.parse(date_created)
                                    else:
                                        date_created_obj = None

                                    if not date_created_obj or date_created_obj >= data_60_dias_antes:
                                        cancellations = "cancelled" if pedido.get("status") == "cancelled" else "active"

                                        for item in pedido.get("order_items", []):
                                            unit_price = float(item.get("unit_price", 0.0))
                                            quantity = int(item.get("quantity", 0))
                                            sale_fee = float(item.get("sale_fee", 0.0))
                                            title = item.get("item", {}).get("title", "")
                                            mlb = item.get("item", {}).get("id", "")
                                            sku = item.get("item", {}).get("seller_sku", "")
                                            shipment = pedido.get('shipping', {})
                                            shipment_id = shipment.get('id', "")
                                            buyer_id = pedido.get('buyer', {}).get('id', "")

                                            # Delay para evitar rate limit
                                            await asyncio.sleep(random.uniform(0.5, 1.5))

                                            envio_details = await fetch_shipment(access_token, shipment_id, api_url,
                                                                                 session)

                                            # Tentativa adicional para billing details em caso de falha
                                            billing_details = None
                                            for _ in range(2):  # Duas tentativas para billing
                                                billing_details = await fetch_billing_details(access_token, order_id,
                                                                                              api_url, session)
                                                if billing_details is not None:
                                                    break
                                                await asyncio.sleep(1)

                                            if envio_details:
                                                print(f"Inserindo pedido {order_id} no banco de dados.")

                                                paid_by = billing_details["paid_by"] if billing_details else "unknown"
                                                release_date = billing_details["release_date"] if billing_details else \
                                                envio_details["release_date"]

                                                # Cálculo de taxas
                                                mlb_taxa_fixa_um_real = ["MLB3776836339", "MLB3804566539",
                                                                         "MLB5116841236"]
                                                if unit_price < 79:
                                                    if mlb in mlb_taxa_fixa_um_real:
                                                        taxa_fixa_ml = 1 * quantity
                                                    else:
                                                        taxa_fixa_ml = 6 * quantity
                                                else:
                                                    taxa_fixa_ml = 0

                                                comissoes = (sale_fee * quantity) - taxa_fixa_ml
                                                comissao_percent = comissoes / (
                                                            unit_price * quantity) if unit_price and quantity else 0

                                                cursor.execute('''
                                                    INSERT OR REPLACE INTO vendas_ml (
                                                        "ID Pedido", "Preco Unitario", "Quantidade", "Data da Venda", "Taxa Mercado Livre",
                                                        "Frete", "Conta", "Cancelamentos", "Titulo", "MLB", "SKU", "Codigo Envio", "Comprador",
                                                        "Modo Envio", "Custo Frete Base", "Custo Frete Opcional", "Custo Pedido Frete",
                                                        "Custo Lista Frete", "Custo Total Frete", "Tipo Logistica", "Pago Por",
                                                        "Situacao", "Situacao Entrega", "Data Liberacao",
                                                        "Taxa Fixa ML", "Comissoes", "Comissao (%)"
                                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                                ''', (
                                                    order_id,
                                                    unit_price,
                                                    quantity,
                                                    date_created_br,
                                                    sale_fee,
                                                    envio_details["total_shipping_cost"],
                                                    traduzir_valores("Conta", seller_id),
                                                    cancellations,
                                                    title,
                                                    mlb,
                                                    sku,
                                                    shipment_id,
                                                    buyer_id,
                                                    envio_details["shipping_mode"],
                                                    envio_details["shipping_base_cost"],
                                                    envio_details["shipping_option_cost"],
                                                    envio_details["shipping_order_cost"],
                                                    envio_details["shipping_list_cost"],
                                                    envio_details["total_shipping_cost"],
                                                    traduzir_valores("Tipo Logistica", envio_details["logistic_type"]),
                                                    paid_by,
                                                    traduzir_valores("Situacao", envio_details["status"]),
                                                    envio_details["delivery_status"],
                                                    release_date,
                                                    taxa_fixa_ml,
                                                    comissoes,
                                                    comissao_percent
                                                ))
                                                conn.commit()
                                except ValueError:
                                    print(f"Data de criação inválida para o pedido {order_id}: {date_created}")
                                    conn.commit()
                                except Exception as e:
                                    print(f"Erro ao processar pedido {order_id}: {e}")
                                    conn.commit()
                        offset += limit
                    else:
                        print(f"Erro API ML: {response.status} {await response.text()}")
                        break
            except Exception as e:
                print(f"Erro ao buscar pedidos para o Seller ID {seller_id}: {e}")
                break
        conn.commit()


def atualizar_traducoes_existentes():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE vendas_ml SET \"Conta\" = 'Comercial' WHERE \"Conta\" = '202989490'")
        cursor.execute("UPDATE vendas_ml SET \"Conta\" = 'Camping' WHERE \"Conta\" = '702704896'")
        cursor.execute("UPDATE vendas_ml SET \"Conta\" = 'Pesca' WHERE \"Conta\" = '263678949'")
        cursor.execute("UPDATE vendas_ml SET \"Conta\" = 'Toys' WHERE \"Conta\" = '555536943'")
        cursor.execute(
            "UPDATE vendas_ml SET \"Tipo Logistica\" = 'Full' WHERE LOWER(\"Tipo Logistica\") LIKE '%fulfillment%'")
        cursor.execute(
            "UPDATE vendas_ml SET \"Tipo Logistica\" = 'Ponto de Coleta' WHERE LOWER(\"Tipo Logistica\") LIKE '%xd_drop_off%'")
        cursor.execute(
            "UPDATE vendas_ml SET \"Tipo Logistica\" = 'Flex' WHERE LOWER(\"Tipo Logistica\") LIKE '%self_service%'")
        cursor.execute(
            "UPDATE vendas_ml SET \"Situacao\" = 'Pronto para Envio' WHERE LOWER(\"Situacao\") LIKE '%ready_to_ship%'")
        cursor.execute("UPDATE vendas_ml SET \"Situacao\" = 'Enviado' WHERE LOWER(\"Situacao\") LIKE '%shipped%'")
        cursor.execute("UPDATE vendas_ml SET \"Situacao\" = 'Cancelado' WHERE LOWER(\"Situacao\") LIKE '%cancelled%'")
        cursor.execute("UPDATE vendas_ml SET \"Situacao\" = 'Pendente' WHERE LOWER(\"Situacao\") LIKE '%pending%'")
        cursor.execute("UPDATE vendas_ml SET \"Situacao\" = 'Entregue' WHERE LOWER(\"Situacao\") LIKE '%delivered%'")
        conn.commit()
    print("Traduções para registros existentes concluídas!")


# --- MIGRAÇÃO E CÁLCULO DA TABELA repasses_ml ---
def migrar_para_repasses_ml():
    print("[PASSO 3] Migrando dados essenciais para repasses_ml...")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(vendas_ml)")
        vendas_cols = [c[1] for c in cursor.fetchall()]
        # Garante que todas as colunas existem antes de migrar
        required = [
            "ID Pedido", "Data da Venda", "Conta", "Preco Unitario", "Quantidade",
            "Taxa Fixa ML", "Comissoes", "Custo Total Frete", "Data Liberacao"
        ]
        missing = [c for c in required if c not in vendas_cols]
        if missing:
            print("❌ Faltando colunas na vendas_ml:", missing)
            return

        cursor.execute('''
            INSERT OR REPLACE INTO repasses_ml (
                "ID Pedido", "Data da Venda", "Conta", "Preco Unitario", "Quantidade",
                "Taxa Fixa ML", "Comissoes", "Frete Seller", "Data Liberacao"
            )
            SELECT
                "ID Pedido", "Data da Venda", "Conta", "Preco Unitario", "Quantidade",
                "Taxa Fixa ML", "Comissoes", "Custo Total Frete", "Data Liberacao"
            FROM vendas_ml
            WHERE "ID Pedido" IS NOT NULL
        ''')
        conn.commit()
    print("Migração finalizada.")


def atualizar_data_repasse_ml():
    conn = sqlite3.connect(DB_PATH)
    repasses = pd.read_sql_query("SELECT * FROM repasses_ml", conn)

    def calcular_data_repasse(row):
        data_base = pd.to_datetime(row['Data da Venda'], errors='coerce')
        tipo = (row['Tipo Logistica'] or '').strip().lower()
        if tipo == 'flex':
            return (data_base + pd.Timedelta(days=7)).strftime('%d/%m/%Y')
        elif tipo == 'full':
            return (data_base + pd.Timedelta(days=10)).strftime('%d/%m/%Y')
        else:
            return (data_base + pd.Timedelta(days=20)).strftime('%d/%m/%Y')

    # Se por acaso não existe a coluna Tipo Logistica em repasses_ml, busque de vendas_ml:
    if 'Tipo Logistica' not in repasses.columns:
        vendas = pd.read_sql_query("SELECT \"ID Pedido\", \"Tipo Logistica\" FROM vendas_ml", conn)
        repasses = repasses.merge(vendas, left_on="ID Pedido", right_on="ID Pedido", how="left")

    repasses['DATA_REPASSE'] = repasses.apply(calcular_data_repasse, axis=1)
    repasses.to_sql("repasses_ml", conn, if_exists="replace", index=False)
    conn.close()
    print("✅ DATA_REPASSE atualizada na tabela repasses_ml (ML)")

def calcular_colunas_repasses():
    print("[PASSO 4] Calculando Total da Venda, Total Custo e Valor do Repasse na tabela repasses_ml...")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        # Garante as colunas, caso sejam novas (idempotente)
        colunas_necessarias = ["Total da Venda", "Total Custo", "Valor do Repasse"]
        cursor.execute("PRAGMA table_info(repasses_ml)")
        cols = [c[1] for c in cursor.fetchall()]
        for c in colunas_necessarias:
            if c not in cols:
                cursor.execute(f'ALTER TABLE repasses_ml ADD COLUMN "{c}" REAL')
        # Atualiza os cálculos
        cursor.execute('''
            UPDATE repasses_ml SET
                "Total da Venda" = COALESCE("Preco Unitario",0) * COALESCE("Quantidade",0),
                "Total Custo" = COALESCE("Taxa Fixa ML",0) + COALESCE("Comissoes",0) + COALESCE("Frete Seller",0),
                "Valor do Repasse" = COALESCE("Total da Venda",0) - COALESCE("Total Custo",0)
        ''')
        conn.commit()
atualizar_data_repasse_ml()

def atualizar_entradas_financeiras_ml():
    print("[PASSO 5] Atualizando tabela entradas_financeiras...")
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM repasses_ml")
        rows = cursor.fetchall()
        if not rows:
            print("⚠️ Nenhum registro encontrado em repasses_ml!")
            return

        ok, fail = 0, 0
        for row in rows:
            (
                id_pedido, data_venda, conta, preco_unit, qtd,
                taxa_fixa, comissoes, frete_seller, data_liberacao,
                total_venda, total_custo, valor_repasse, data_repasse,  # <-- DATA_REPASSE agora!
                # ...
            ) = row
            # Use data_repasse no insert

            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO entradas_financeiras (
                        tipo, pedido_id, data_venda, data_liberacao,
                        valor_total, valor_liquido, comissoes, taxas, frete,
                        status, origem_conta, observacoes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    'ml',                         # tipo
                    id_pedido,                    # pedido_id
                    data_venda,                   # data_venda
                    data_liberacao,               # data_liberacao
                    total_venda,                  # valor_total
                    valor_repasse,                # valor_liquido
                    comissoes,                    # comissoes
                    taxa_fixa,                    # taxas
                    frete_seller,                 # frete
                    'Recebido' if data_liberacao else 'Pendente', # status
                    conta,                        # origem_conta
                    ''                            # observacoes (deixa vazio, se não quiser preencha aqui)
                ))
                ok += 1
            except Exception as e:
                print(f"Erro ao inserir pedido {id_pedido}: {e}")
                fail += 1
        conn.commit()
    print(f"Entradas financeiras atualizadas. Sucesso: {ok} | Falhas: {fail}")

# === PIPELINE ÚNICO ===
async def pipeline_completo():
    print("=== PROCESSAMENTO AUTOMATIZADO MERCADO LIVRE ===")
    inicializar_banco()
    print("[PASSO 1] Buscando vendas na API Mercado Livre e alimentando tabela vendas_ml...")

    contas = [
        {"nome": "TOYS", "client_id": os.getenv("CLIENT_ID_TOYS"), "client_secret": os.getenv("CLIENT_SECRET_TOYS"),
         "access_token": os.getenv("ACCESS_TOKEN_TOYS"), "refresh_token": os.getenv("REFRESH_TOKEN_TOYS"),
         "seller_id": os.getenv("SELLER_ID_TOYS")},
        {"nome": "COMERCIAL", "client_id": os.getenv("CLIENT_ID_COMERCIAL"),
         "client_secret": os.getenv("CLIENT_SECRET_COMERCIAL"), "access_token": os.getenv("ACCESS_TOKEN_COMERCIAL"),
         "refresh_token": os.getenv("REFRESH_TOKEN_COMERCIAL"), "seller_id": os.getenv("SELLER_ID_COMERCIAL")},
        {"nome": "PESCA", "client_id": os.getenv("CLIENT_ID_PESCA"), "client_secret": os.getenv("CLIENT_SECRET_PESCA"),
         "access_token": os.getenv("ACCESS_TOKEN_PESCA"), "refresh_token": os.getenv("REFRESH_TOKEN_PESCA"),
         "seller_id": os.getenv("SELLER_ID_PESCA")},
        {"nome": "CAMPING", "client_id": os.getenv("CLIENT_ID_CAMPING"),
         "client_secret": os.getenv("CLIENT_SECRET_CAMPING"), "access_token": os.getenv("ACCESS_TOKEN_CAMPING"),
         "refresh_token": os.getenv("REFRESH_TOKEN_CAMPING"), "seller_id": os.getenv("SELLER_ID_CAMPING")},
    ]

    api_url = os.getenv("API_URL")

    async with aiohttp.ClientSession() as session:
        for conta in contas:
            if conta["access_token"] and conta["client_id"]:
                print(f"Verificando se o token está válido para a conta {conta['nome']}...")
                new_access_token, new_refresh_token = await refresh_token(
                    conta["client_id"], conta["client_secret"], conta["refresh_token"], api_url, session
                )
                if new_access_token and new_refresh_token:
                    atualizar_env_token(conta['nome'], new_access_token, new_refresh_token)
                    print(f"Tokens atualizados para a conta {conta['nome']}.")
                    conta["access_token"] = new_access_token
                    conta["refresh_token"] = new_refresh_token

                print(f"Buscando pedidos e envios para a conta {conta['nome']} (Seller ID: {conta['seller_id']})...")
                await buscar_pedidos_e_envios(conta["access_token"], conta["seller_id"], api_url, session)
            else:
                print(f"Credenciais não encontradas para a conta {conta['nome']}. Verifique o arquivo .env.")

    print("Vendas buscadas e tabela vendas_ml alimentada.")
    print("[PASSO 2] Traduzindo valores para PT-BR e normalizando tabela vendas_ml...")
    atualizar_traducoes_existentes()
    print("Traduções aplicadas.")
    migrar_para_repasses_ml()
    calcular_colunas_repasses()
    atualizar_entradas_financeiras_ml()
    print("=== FINALIZADO! Sistema Mercado Livre sincronizado e automatizado ===")


# --- EXECUÇÃO ---
if __name__ == "__main__":
    asyncio.run(pipeline_completo())