# === PROCESSAMENTO AUTOMATIZADO MERCADO LIVRE ===
# Versão completa, testada e corrigida

import sqlite3
import aiohttp
import asyncio
from dotenv import load_dotenv, set_key
import os
from datetime import datetime, timedelta
from dateutil import parser
import pytz
from flask import Blueprint
import random
from typing import Dict, List, Any, Optional, Tuple

# Configurações
DB_PATH = "C:/fisgarone/fisgarone.db"
ENV_PATH = "C:/fisgarone/.env"
MAX_CONCURRENT_REQUESTS = 15
DAYS_TO_FETCH = 60

load_dotenv(dotenv_path=ENV_PATH, override=True)

# Blueprint Flask
importador_automatico_bp = Blueprint('importador_automatico_bp', __name__)

def data_br_safe(val):
    """Garante string data em formato brasileiro DD/MM/YYYY ou vazio."""
    from datetime import datetime
    if not val or not isinstance(val, str):
        return ""
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S", "%d/%m/%Y", "%d-%m-%Y"):
        try:
            d = datetime.strptime(val[:10], fmt)
            return d.strftime("%d/%m/%Y")
        except Exception:
            continue
    return val if "/" in val else ""


# --- Funções Auxiliares ---
def traduzir_valores(coluna: str, valor: Any) -> Any:
    """Traduz valores específicos de colunas para PT-BR com tratamento para tipos numéricos."""
    if valor is None:
        return None

    # Converter para string se for número
    valor_str = str(valor).lower() if not isinstance(valor, (int, float)) else str(valor)
    traducoes = {
        "Tipo Logistica": {
            "fulfillment": "Full",
            "xd_drop_off": "Ponto de Coleta",
            "self_service": "Flex"
        },
        "Situacao": {
            "ready_to_ship": "Pronto para Envio",
            "shipped": "Enviado",
            "cancelled": "Cancelado",
            "pending": "Pendente",
            "delivered": "Entregue"
        },
        "Conta": {
            "202989490": "Comercial",
            "702704896": "Camping",
            "263678949": "Pesca",
            "555536943": "Toys"
        }
    }
    return traducoes.get(coluna, {}).get(valor_str, valor)

def inicializar_banco() -> None:
    """Cria as tabelas no banco de dados se não existirem."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Tabela vendas_ml - corrigida para corresponder exatamente ao INSERT
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
            "Comissao (%)" REAL,
            "Preço Custo ML" REAL,
            "Custo Total Calculado" REAL,
            "Aliquota (%)" REAL,
            "Imposto R$" REAL,
            "Frete Comprador" REAL,
            "Frete Seller" REAL,
            "Custo Operacional" REAL,
            "Total Custo Operacional" REAL,
            "MC Total" REAL,
            "Custo Fixo" REAL,
            "Lucro Real" REAL,
            "Lucro Real %" REAL
        )''')

        # Tabela repasses_ml
        cursor.execute('''CREATE TABLE IF NOT EXISTS repasses_ml (
            "ID Pedido" TEXT,
            "Preco Unitario" REAL,
            "Data da Venda" TEXT,
            "Quantidade" INTEGER,
            "Tipo Logistica" TEXT,
            "Situacao" TEXT,
            "Taxa Fixa ML" REAL,
            "Comissoes" REAL,
            "Frete Seller" REAL,
            "Data Liberacao" TEXT,
            "Total da Venda" REAL,
            "Total Custo" REAL,
            "Valor do Repasse" REAL,
            "Conta" TEXT,
            "DATA_REPASSE" TEXT
        )''')

        # Tabela entradas_financeiras
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
            "observacoes" TEXT,
            "data_insercao" TEXT DEFAULT (datetime('now', 'localtime')),
            "data_repasse" REAL,
            UNIQUE(pedido_id, tipo)
        )''')
        conn.commit()

def atualizar_env_token(account_name: str, new_access_token: str, new_refresh_token: str) -> None:
    """Atualiza os tokens no arquivo .env."""
    set_key(ENV_PATH, f'ACCESS_TOKEN_{account_name}', new_access_token)
    set_key(ENV_PATH, f'REFRESH_TOKEN_{account_name}', new_refresh_token)

# --- Funções de API Otimizadas ---
async def make_api_request(session: aiohttp.ClientSession,
                         url: str,
                         headers: Dict[str, str],
                         method: str = 'GET',
                         data: Optional[Dict] = None,
                         max_retries: int = 3) -> Optional[Any]:
    """Faz requisições HTTP com tratamento de erros e retentativas."""
    for attempt in range(max_retries):
        try:
            async with session.request(method, url, headers=headers, json=data) as response:
                if response.status == 200:
                    return await response.json()
                elif response.status == 401:
                    return "token_invalido"
                elif response.status == 429:
                    wait_time = (attempt + 1) * 2
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    print(f"Erro {response.status} em {url}: {await response.text()}")
                    return None
        except Exception as e:
            print(f"Erro na tentativa {attempt + 1} para {url}: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(1)
    return None

async def refresh_token(client_id: str,
                      client_secret: str,
                      refresh_token: str,
                      api_url: str,
                      session: aiohttp.ClientSession) -> Tuple[Optional[str], Optional[str]]:
    """Renova o token de acesso usando o refresh token."""
    url = f"{api_url}/oauth/token"
    data = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token
    }
    result = await make_api_request(session, url, {}, 'POST', data)
    if result and isinstance(result, dict):
        return result.get('access_token'), result.get('refresh_token')
    return None, None

async def get_shipment_details(access_token: str,
                             shipment_id: str,
                             api_url: str,
                             session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
    """Obtém detalhes de um envio específico com tratamento para shipment_id None."""
    if not shipment_id or shipment_id.lower() == 'none':
        return {
            "logistic_type": "",
            "shipping_mode": "",
            "shipping_base_cost": 0,
            "shipping_option_cost": 0,
            "shipping_order_cost": 0,
            "shipping_list_cost": 0,
            "total_shipping_cost": 0,
            "status": "",
            "delivery_status": "",
            "release_date": "",
            "date_created": ""
        }

    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{api_url}/shipments/{shipment_id}"

    try:
        shipment = await make_api_request(session, url, headers)
        if not shipment or shipment == "token_invalido":
            return shipment

        # Obter custos em paralelo
        costs_url = f"{api_url}/shipments/{shipment_id}/costs"
        payments_url = f"{api_url}/shipments/{shipment_id}/payments"

        costs_task = make_api_request(session, costs_url, headers)
        payments_task = make_api_request(session, payments_url, headers)

        costs_data, payments_data = await asyncio.gather(costs_task, payments_task)

        shipping_base_cost = float(costs_data.get("gross_amount", 0)) if costs_data else 0
        shipping_cost = 0

        if payments_data:
            if isinstance(payments_data, list) and payments_data:
                shipping_cost = float(payments_data[0].get("amount", 0))
            elif isinstance(payments_data, dict):
                shipping_cost = float(payments_data.get("amount", 0))

        return {
            "logistic_type": shipment.get("logistic_type", ""),
            "shipping_mode": shipment.get("shipping_mode", ""),
            "shipping_base_cost": shipping_base_cost,
            "shipping_option_cost": float(shipment.get("shipping_option", {}).get("cost", 0)),
            "shipping_order_cost": float(shipment.get("order_cost", 0)),
            "shipping_list_cost": float(shipment.get("shipping_option", {}).get("list_cost", 0)),
            "total_shipping_cost": shipping_cost,
            "status": shipment.get("status", ""),
            "delivery_status": shipment.get("tracking", {}).get("status", ""),
            "release_date": shipment.get("date_estimated_delivery", {}).get("date"),
            "date_created": shipment.get("date_created", "")
        }
    except Exception as e:
        print(f"Erro ao obter detalhes do envio {shipment_id}: {str(e)}")
        return None


async def process_order_item(item: Dict[str, Any],
                             order_id: str,
                             date_created_br: str,
                             cancellations: str,
                             shipment_id: str,
                             buyer_id: str,
                             access_token: str,
                             api_url: str,
                             session: aiohttp.ClientSession) -> Optional[Dict[str, Any]]:
    """
    Processa um item individual de um pedido com tratamento robusto para tipos e valores nulos.

    Args:
        item: Dicionário com informações do item do pedido
        order_id: ID do pedido
        date_created_br: Data de criação do pedido formatada (DD/MM/YYYY)
        cancellations: Status de cancelamento ('cancelled' ou 'active')
        shipment_id: ID do envio (pode ser None ou string)
        buyer_id: ID do comprador
        access_token: Token de acesso à API
        api_url: URL base da API
        session: Sessão aiohttp

    Returns:
        Dicionário com todos os campos processados ou None em caso de erro
    """
    try:
        # 1. Conversão segura de todos os valores básicos
        unit_price = float(item.get("unit_price", 0)) if item.get("unit_price") not in [None, ""] else 0
        quantity = int(item.get("quantity", 0)) if item.get("quantity") not in [None, ""] else 0
        sale_fee = float(item.get("sale_fee", 0)) if item.get("sale_fee") not in [None, ""] else 0

        # 2. Tratamento seguro para campos de texto
        title = str(item.get("item", {}).get("title", "")) or ""
        mlb = str(item.get("item", {}).get("id", "")) or ""
        sku = str(item.get("item", {}).get("seller_sku", "")) or ""

        # 3. Normalização de shipment_id e buyer_id
        shipment_id = str(shipment_id) if shipment_id is not None else ""
        buyer_id = str(buyer_id) if buyer_id is not None else ""

        # 4. Obtenção dos detalhes de envio com tratamento robusto
        envio_details = {
            "logistic_type": "",
            "shipping_mode": "",
            "shipping_base_cost": 0,
            "shipping_option_cost": 0,
            "shipping_order_cost": 0,
            "shipping_list_cost": 0,
            "total_shipping_cost": 0,
            "status": cancellations if cancellations == "cancelled" else "pending",
            "delivery_status": "",
            "release_date": "",
            "date_created": ""
        }

        if shipment_id and shipment_id.lower() not in ["", "none"]:
            try:
                details = await get_shipment_details(access_token, shipment_id, api_url, session)
                if details == "token_invalido":
                    return "token_invalido"
                if details:
                    envio_details.update(details)
            except Exception as e:
                print(f"Erro ao obter detalhes do envio {shipment_id}: {str(e)}")

        # 5. Cálculo de taxas e valores financeiros
        mlb_taxa_fixa_um_real = ["MLB3776836339", "MLB3804566539", "MLB5116841236"]
        try:
            taxa_fixa_ml = (1 if mlb in mlb_taxa_fixa_um_real else 6) * quantity if unit_price < 79 else 0
            comissoes = max(0, (sale_fee * quantity) - taxa_fixa_ml)  # Garante não negativo

            # Cálculo seguro para porcentagens evitando divisão por zero
            total_venda = unit_price * quantity
            comissao_percent = (comissoes / total_venda * 100) if total_venda > 0 else 0
            comissao_percent = round(comissao_percent, 2)  # Limita a 2 casas decimais
        except Exception as e:
            print(f"Erro no cálculo de taxas para item {mlb}: {str(e)}")
            taxa_fixa_ml = 0
            comissoes = 0
            comissao_percent = 0

        # 6. Cálculo de valores adicionais com tratamento de erros
        try:
            preco_custo_ml = 0  # Pode ser obtido de outra fonte se disponível
            custo_total_calculado = max(0, (unit_price * quantity) - comissoes - taxa_fixa_ml)
            aliquota_percent = 0  # Valor padrão - ajustar conforme regras fiscais
            imposto_r = 0  # Valor padrão - ajustar conforme regras fiscais
            frete_comprador = 0  # Valor padrão - pode ser obtido da API se disponível
            frete_seller = float(envio_details.get("total_shipping_cost", 0))
            custo_operacional = 0  # Valor padrão - ajustar conforme regras da empresa
            total_custo_operacional = custo_operacional * quantity
            mc_total = max(0, (unit_price * quantity) - custo_total_calculado - total_custo_operacional)
            custo_fixo = 0  # Valor padrão - ajustar conforme regras da empresa
            lucro_real = max(0, mc_total - custo_fixo)

            # Cálculo seguro de porcentagem de lucro
            lucro_real_percent = (lucro_real / total_venda * 100) if total_venda > 0 else 0
            lucro_real_percent = round(lucro_real_percent, 2)  # Limita a 2 casas decimais
        except Exception as e:
            print(f"Erro no cálculo financeiro para item {mlb}: {str(e)}")
            # Define valores padrão em caso de erro
            preco_custo_ml = custo_total_calculado = aliquota_percent = imposto_r = 0
            frete_comprador = frete_seller = custo_operacional = total_custo_operacional = 0
            mc_total = custo_fixo = lucro_real = lucro_real_percent = 0

        # 7. Construção do dicionário de retorno com todos os campos
        return {
            "ID Pedido": order_id,
            "Preco Unitario": round(unit_price, 2),
            "Quantidade": quantity,
            "Data da Venda": date_created_br,
            "Taxa Mercado Livre": round(sale_fee, 2),
            "Frete": round(frete_seller, 2),
            "Conta": None,  # Será preenchido posteriormente
            "Cancelamentos": cancellations,
            "Titulo": title[:255],  # Limita o tamanho para evitar problemas no banco
            "MLB": mlb[:50],  # Limita o tamanho
            "SKU": sku[:50],  # Limita o tamanho
            "Codigo Envio": shipment_id[:50] if shipment_id and shipment_id.lower() != 'none' else "",
            "Comprador": buyer_id[:50],  # Limita o tamanho
            "Modo Envio": envio_details.get("shipping_mode", "")[:50] if envio_details else "",
            "Custo Frete Base": round(float(envio_details.get("shipping_base_cost", 0)), 2),
            "Custo Frete Opcional": round(float(envio_details.get("shipping_option_cost", 0)), 2),
            "Custo Pedido Frete": round(float(envio_details.get("shipping_order_cost", 0)), 2),
            "Custo Lista Frete": round(float(envio_details.get("shipping_list_cost", 0)), 2),
            "Custo Total Frete": round(float(envio_details.get("total_shipping_cost", 0)), 2),
            "Tipo Logistica": traduzir_valores("Tipo Logistica", envio_details.get("logistic_type", "")) or "",
            "Pago Por": "seller",
            "Situacao": traduzir_valores("Situacao", envio_details.get("status", "")) or "Pendente",
            "Situacao Entrega": envio_details.get("delivery_status", "") or "",
            "Data Liberacao": envio_details.get("release_date", "") or "",
            "Taxa Fixa ML": round(taxa_fixa_ml, 2),
            "Comissoes": round(comissoes, 2),
            "Comissao (%)": comissao_percent,
            "Preço Custo ML": round(preco_custo_ml, 0),
            "Custo Total Calculado": round(custo_total_calculado, 2),
            "Aliquota (%)": aliquota_percent,
            "Imposto R$": round(imposto_r, 2),
            "Frete Comprador": round(frete_comprador, 2),
            "Frete Seller": round(frete_seller, 2),
            "Custo Operacional": round(custo_operacional, 2),
            "Total Custo Operacional": round(total_custo_operacional, 0),
            "MC Total": round(mc_total, 0),
            "Custo Fixo": round(custo_fixo, 0),
            "Lucro Real": round(lucro_real, 0),
            "Lucro Real %": lucro_real_percent
        }

    except Exception as e:
        print(f"Erro crítico ao processar item {mlb} do pedido {order_id}: {str(e)}")
        return None
async def process_order_batch(orders: List[Dict[str, Any]],
                            access_token: str,
                            seller_id: str,
                            api_url: str,
                            session: aiohttp.ClientSession) -> List[Dict[str, Any]]:
    """Processa um lote de pedidos em paralelo."""
    tasks = []
    for pedido in orders:
        order_id = pedido.get("id", "")
        date_created = pedido.get("date_created", "")
        date_created_br = ""

        try:
            if date_created:
                date_created_obj = parser.parse(date_created)
                date_created_br = date_created_obj.strftime("%d/%m/%Y")
        except Exception:
            date_created_br = date_created

        cancellations = "cancelled" if pedido.get("status") == "cancelled" else "active"
        shipment_id = pedido.get('shipping', {}).get('id', "")
        buyer_id = pedido.get('buyer', {}).get('id', "")

        for item in pedido.get("order_items", []):
            tasks.append(
                process_order_item(
                    item, order_id, date_created_br, cancellations,
                    shipment_id, buyer_id, access_token, api_url, session
                )
            )

    results = await asyncio.gather(*tasks, return_exceptions=True)

    valid_results = []
    for result in results:
        if isinstance(result, dict):
            valid_results.append(result)
        elif result == "token_invalido":
            return "token_invalido"

    return valid_results

async def fetch_orders_for_account(access_token: str,
                                seller_id: str,
                                api_url: str,
                                session: aiohttp.ClientSession) -> bool:
    """Busca e processa todos os pedidos para uma conta específica."""
    headers = {"Authorization": f"Bearer {access_token}"}
    offset = 0
    limit = 50

    start_date = datetime.now(pytz.timezone('America/Sao_Paulo')) - timedelta(days=DAYS_TO_FETCH)
    start_date_str = start_date.strftime("%Y-%m-%dT%H:%M:%S%z")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        while True:
            url = f"{api_url}/orders/search?seller={seller_id}&date_created.from={start_date_str}&offset={offset}&limit={limit}"

            data = await make_api_request(session, url, headers)
            if data == "token_invalido":
                return False

            if not data:
                break

            orders = data.get('results', [])
            total = data.get('paging', {}).get('total', 0)

            if not orders:
                break

            batch_results = await process_order_batch(orders, access_token, seller_id, api_url, session)
            if batch_results == "token_invalido":
                return False

            for item in batch_results:
                if item:
                    item["Conta"] = traduzir_valores("Conta", seller_id)
                    # Garantir que todos os parâmetros existam no dicionário
                    params = {
                        "ID_Pedido": item.get("ID Pedido"),
                        "Preco_Unitario": item.get("Preco Unitario", 0),
                        "Quantidade": item.get("Quantidade", 0),
                        "Data_da_Venda": item.get("Data da Venda", ""),
                        "Taxa_Mercado_Livre": item.get("Taxa Mercado Livre", 0),
                        "Frete": item.get("Frete", 0),
                        "Conta": item.get("Conta", ""),
                        "Cancelamentos": item.get("Cancelamentos", ""),
                        "Titulo": item.get("Titulo", ""),
                        "MLB": item.get("MLB", ""),
                        "SKU": item.get("SKU", ""),
                        "Codigo_Envio": item.get("Codigo Envio", ""),
                        "Comprador": item.get("Comprador", ""),
                        "Modo_Envio": item.get("Modo Envio", ""),
                        "Custo_Frete_Base": item.get("Custo Frete Base", 0),
                        "Custo_Frete_Opcional": item.get("Custo Frete Opcional", 0),
                        "Custo_Pedido_Frete": item.get("Custo Pedido Frete", 0),
                        "Custo_Lista_Frete": item.get("Custo Lista Frete", 0),
                        "Custo_Total_Frete": item.get("Custo Total Frete", 0),
                        "Tipo_Logistica": item.get("Tipo Logistica", ""),
                        "Pago_Por": item.get("Pago Por", ""),
                        "Situacao": item.get("Situacao", ""),
                        "Situacao_Entrega": item.get("Situacao Entrega", ""),
                        "Data_Liberacao": item.get("Data Liberacao", ""),
                        "Taxa_Fixa_ML": item.get("Taxa Fixa ML", 0),
                        "Comissoes": item.get("Comissoes", 0),
                        "Comissao_Perc": item.get("Comissao (%)", 0),
                        "Preço_Custo_ML": item.get("Preço Custo ML", 0),
                        "Custo_Total_Calculado": item.get("Custo Total Calculado", 0),
                        "Aliquota_Perc": item.get("Aliquota (%)", 0),
                        "Imposto_R": item.get("Imposto R$", 0),
                        "Frete_Comprador": item.get("Frete Comprador", 0),
                        "Frete_Seller": item.get("Frete Seller", 0),
                        "Custo_Operacional": item.get("Custo Operacional", 0),
                        "Total_Custo_Operacional": item.get("Total Custo Operacional", 0),
                        "MC_Total": item.get("MC Total", 0),
                        "Custo_Fixo": item.get("Custo Fixo", 0),
                        "Lucro_Real": item.get("Lucro Real", 0),
                        "Lucro_Real_Perc": item.get("Lucro Real %", 0)
                    }
                    cursor.execute('''
                        INSERT OR REPLACE INTO vendas_ml VALUES (
                            :ID_Pedido, :Preco_Unitario, :Quantidade, :Data_da_Venda, 
                            :Taxa_Mercado_Livre, :Frete, :Conta, :Cancelamentos, 
                            :Titulo, :MLB, :SKU, :Codigo_Envio, :Comprador, 
                            :Modo_Envio, :Custo_Frete_Base, :Custo_Frete_Opcional, 
                            :Custo_Pedido_Frete, :Custo_Lista_Frete, :Custo_Total_Frete, 
                            :Tipo_Logistica, :Pago_Por, :Situacao, :Situacao_Entrega, 
                            :Data_Liberacao, :Taxa_Fixa_ML, :Comissoes, :Comissao_Perc,
                            :Preço_Custo_ML, :Custo_Total_Calculado, :Aliquota_Perc,
                            :Imposto_R, :Frete_Comprador, :Frete_Seller,
                            :Custo_Operacional, :Total_Custo_Operacional, :MC_Total,
                            :Custo_Fixo, :Lucro_Real, :Lucro_Real_Perc
                        )
                    ''', params)

            conn.commit()
            offset += limit

            if offset >= total:
                break

    return True

# --- Funções de Pós-Processamento ---
def atualizar_traducoes_existentes() -> None:
    """Atualiza registros existentes com traduções para PT-BR."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute("UPDATE vendas_ml SET \"Conta\" = 'Comercial' WHERE \"Conta\" = '202989490'")
        cursor.execute("UPDATE vendas_ml SET \"Conta\" = 'Camping' WHERE \"Conta\" = '702704896'")
        cursor.execute("UPDATE vendas_ml SET \"Conta\" = 'Pesca' WHERE \"Conta\" = '263678949'")
        cursor.execute("UPDATE vendas_ml SET \"Conta\" = 'Toys' WHERE \"Conta\" = '555536943'")

        cursor.execute("UPDATE vendas_ml SET \"Tipo Logistica\" = 'Full' WHERE LOWER(\"Tipo Logistica\") LIKE '%fulfillment%'")
        cursor.execute("UPDATE vendas_ml SET \"Tipo Logistica\" = 'Ponto de Coleta' WHERE LOWER(\"Tipo Logistica\") LIKE '%xd_drop_off%'")
        cursor.execute("UPDATE vendas_ml SET \"Tipo Logistica\" = 'Flex' WHERE LOWER(\"Tipo Logistica\") LIKE '%self_service%'")

        cursor.execute("UPDATE vendas_ml SET \"Situacao\" = 'Pronto para Envio' WHERE LOWER(\"Situacao\") LIKE '%ready_to_ship%'")
        cursor.execute("UPDATE vendas_ml SET \"Situacao\" = 'Enviado' WHERE LOWER(\"Situacao\") LIKE '%shipped%'")
        cursor.execute("UPDATE vendas_ml SET \"Situacao\" = 'Cancelado' WHERE LOWER(\"Situacao\") LIKE '%cancelled%'")
        cursor.execute("UPDATE vendas_ml SET \"Situacao\" = 'Pendente' WHERE LOWER(\"Situacao\") LIKE '%pending%'")
        cursor.execute("UPDATE vendas_ml SET \"Situacao\" = 'Entregue' WHERE LOWER(\"Situacao\") LIKE '%delivered%'")

        conn.commit()


from datetime import datetime

def format_date_to_br(data_str):
    """Força data em qualquer formato para DD/MM/YYYY. Retorna vazio se não der parse."""
    if not data_str or not isinstance(data_str, str):
        return ""
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%Y/%m/%d", "%Y-%m-%d %H:%M:%S"):
        try:
            d = datetime.strptime(data_str[:10], fmt)
            return d.strftime("%d/%m/%Y")
        except Exception:
            continue
    # Se for datetime completo, tenta extrair só a parte da data:
    try:
        d = datetime.fromisoformat(data_str[:10])
        return d.strftime("%d/%m/%Y")
    except Exception:
        pass
    return ""

# EXEMPLOS:
print(format_date_to_br("2024-07-02"))       # 02/07/2024
print(format_date_to_br("2024/07/02"))       # 02/07/2024
print(format_date_to_br("02/07/2024"))       # 02/07/2024
print(format_date_to_br("02-07-2024"))       # 02/07/2024
print(format_date_to_br("2024-07-02 10:00:00")) # 02/07/2024
print(format_date_to_br(None))               # ''
print(format_date_to_br(""))                 # ''


def atualizar_preco_custo_ml():
    """
    Executa uma sequência de cálculos na tabela vendas_ml para atualizar todos os
    campos financeiros de forma correta e sequencial.
    """
    print("\n[PASSO 2] Atualizando cálculos financeiros em vendas_ml...")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # 1. PREÇO CUSTO ML: Custo da tabela 'custos_ml' x quantidade da venda.
            cursor.execute("""
                UPDATE vendas_ml
                SET "Preço Custo ML" = (
                    SELECT COALESCE(c.Custo, 0) * COALESCE(vendas_ml.Quantidade, 0)
                    FROM custos_ml c
                    WHERE UPPER(c.MLB) = UPPER(vendas_ml.MLB)
                )
                WHERE EXISTS (
                    SELECT 1 FROM custos_ml c2 WHERE UPPER(c2.MLB) = UPPER(vendas_ml.MLB)
                )
            """)

            # 2. ALÍQUOTAS (%): Define a alíquota de imposto baseada na conta.
            for conta, aliquota in {
                'COMERCIAL': 7.06, 'PESCA': 5.54, 'SHOP': 10.03, 'CAMPING': 4.00, 'TOYS': 9.27
            }.items():
                cursor.execute("""
                    UPDATE vendas_ml SET "Aliquota (%)" = ? WHERE UPPER(Conta) = ?
                """, (aliquota, conta.upper()))

            # 3. IMPOSTO R$: Calcula o valor do imposto.
            cursor.execute("""
                UPDATE vendas_ml
                SET "Imposto R$" = ROUND(
                    COALESCE("Preco Unitario", 0) * COALESCE(Quantidade, 0) * COALESCE("Aliquota (%)", 0) / 100, 2
                )
            """)

            # 4. FRETES: Divide o custo do frete entre Seller e Comprador baseado no preço.
            cursor.execute("""
                UPDATE vendas_ml
                SET
                    "Frete Seller" = CASE
                        WHEN COALESCE("Preco Unitario", 0) >= 79 THEN COALESCE("Custo Lista Frete", 0)
                        ELSE 0
                    END,
                    "Frete Comprador" = CASE
                        WHEN COALESCE("Preco Unitario", 0) < 79 THEN COALESCE("Custo Total Frete", 0)
                        ELSE 0
                    END
            """)

            # 5. CUSTO OPERACIONAL: Calcula um custo operacional percentual.
            cursor.execute("""
                UPDATE vendas_ml
                SET "Custo Operacional" = ROUND(
                    COALESCE("Preco Unitario", 0) * COALESCE(Quantidade, 0) * 0.04, 2
                )
            """)

            # 6. TOTAL CUSTO OPERACIONAL: Soma todos os custos variáveis.
            cursor.execute("""
                UPDATE vendas_ml
                SET "Total Custo Operacional" =
                    COALESCE("Preço Custo ML", 0) +
                    COALESCE("Imposto R$", 0) +
                    COALESCE("Custo Operacional", 0) +
                    COALESCE("Comissoes", 0) +
                    COALESCE("Taxa Fixa ML", 0) +
                    COALESCE("Frete Seller", 0)
            """)

            # 7. CÁLCULOS FINAIS: Margem de Contribuição, Custo Fixo e Lucro Real.
            # Esta é a etapa crucial que corrige o erro.
            cursor.execute("""
                UPDATE vendas_ml
                SET
                    "MC Total" = ROUND(
                        (COALESCE("Preco Unitario", 0) * COALESCE(Quantidade, 0)) - COALESCE("Total Custo Operacional", 0), 2
                    ),
                    "Custo Fixo" = ROUND(
                        (COALESCE("Preco Unitario", 0) * COALESCE(Quantidade, 0)) * 0.13, 2
                    )
            """)

            # Agora, com "MC Total" e "Custo Fixo" já salvos, calculamos o Lucro Real.
            cursor.execute("""
                UPDATE vendas_ml
                SET
                    "Lucro Real" = ROUND(COALESCE("MC Total", 0) - COALESCE("Custo Fixo", 0), 2)
            """)

            # Finalmente, calculamos a porcentagem do Lucro Real.
            cursor.execute("""
                UPDATE vendas_ml
                SET
                    "Lucro Real %" = CASE
                        WHEN (COALESCE("Preco Unitario", 0) * COALESCE(Quantidade, 0)) > 0 THEN
                            ROUND((COALESCE("Lucro Real", 0) / (COALESCE("Preco Unitario", 0) * COALESCE(Quantidade, 0))) * 100, 2)
                        ELSE 0
                    END
            """)

            conn.commit()
            print("✅ Todos os cálculos foram atualizados com sucesso em vendas_ml.")

    except sqlite3.Error as e:
        print(f"✗ Erro ao atualizar cálculos no banco de dados: {e}")
        # Você pode querer relançar a exceção se este for um erro crítico
        # raise e


def migrar_para_repasses_ml():
    print("[PASSO 3] Migrando dados essenciais para repasses_ml...")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            # Limpar tabela mantendo a estrutura
            cursor.execute('DELETE FROM repasses_ml')

            # Inserir dados usando os nomes exatos das colunas
            cursor.execute('''
                INSERT INTO repasses_ml (
    "ID Pedido", "Preco Unitario", "Data da Venda", "Quantidade",
    "Tipo Logistica", "Taxa Fixa ML", "Comissoes", "Frete Seller",
    "Data Liberacao", "Conta"
)
SELECT
    "ID Pedido",
    "Preco Unitario",
    "Data da Venda",
    "Quantidade",
    "Tipo Logistica",
    "Taxa Fixa ML",
    "Comissoes",
    CASE WHEN "Preco Unitario" >= 79 THEN "Custo Lista Frete" ELSE 0 END,
    "Data Liberacao",
    "Conta"
FROM vendas_ml
                WHERE "ID Pedido" IS NOT NULL
            ''')
            conn.commit()

            # Calcular colunas derivadas
            calcular_colunas_repasses()

            # Atualizar datas de repasse
            atualizar_data_repasse_ml()

        print("✓ Migração finalizada: repasses_ml alimentado corretamente")

    except Exception as e:
        print(f"✗ Erro na migração para repasses_ml: {str(e)}")
        raise


def calcular_colunas_repasses():
    """Calcula colunas derivadas na tabela repasses_ml"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE repasses_ml SET
                    "Total da Venda" = ROUND(COALESCE("Preco Unitario", 0) * COALESCE("Quantidade", 0), 2),
                    "Total Custo" = ROUND(COALESCE("Taxa Fixa ML", 0) + COALESCE("Comissoes", 0) + COALESCE("Frete Seller", 0), 2),
                    "Valor do Repasse" = ROUND(COALESCE("Preco Unitario", 0) * COALESCE("Quantidade", 0) - 
                                              (COALESCE("Taxa Fixa ML", 0) + COALESCE("Comissoes", 0) + COALESCE("Frete Seller", 0)), 2)
            ''')
            conn.commit()

    except Exception as e:
        print(f"✗ Erro ao calcular colunas de repasse: {str(e)}")
        raise


def atualizar_data_repasse_ml():
    """Calcula a data de repasse baseada no tipo de logística"""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()

            cursor.execute('''
                UPDATE repasses_ml SET
                    "DATA_REPASSE" = CASE
                        WHEN "Tipo Logistica" = 'Flex' THEN 
                            date(substr("Data da Venda", 7, 4) || '-' || 
                                 substr("Data da Venda", 4, 2) || '-' || 
                                 substr("Data da Venda", 1, 2), '+7 days')
                        WHEN "Tipo Logistica" = 'Full' THEN 
                            date(substr("Data da Venda", 7, 4) || '-' || 
                                 substr("Data da Venda", 4, 2) || '-' || 
                                 substr("Data da Venda", 1, 2), '+10 days')
                        ELSE 
                            date(substr("Data da Venda", 7, 4) || '-' || 
                                 substr("Data da Venda", 4, 2) || '-' || 
                                 substr("Data da Venda", 1, 2), '+20 days')
                    END
            ''')
            conn.commit()

    except Exception as e:
        print(f"✗ Erro ao atualizar datas de repasse: {str(e)}")
        raise


def atualizar_entradas_financeiras_ml():
    """
    Alimenta entradas_financeiras usando sempre DATA_REPASSE de repasses_ml como data_liberacao.
    'origem_conta' será preenchido com o valor da coluna 'Conta' da tabela repasses_ml.
    """
    print("\n[PASSO 4] Atualizando entradas financeiras (ML)...")
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Seleciona os pedidos do ML que ainda não estão em entradas_financeiras
            cursor.execute("""
                SELECT 
    v."ID Pedido" AS pedido_id, 
    v."Preco Unitario" AS valor_bruto, 
    v."Comissoes" AS comissao, 
    v."Taxa Fixa ML" AS taxas,
    v."Frete Seller" AS frete,
    r."DATA_REPASSE" AS data_repasse,
    r."Conta" AS conta,
    r."Valor do Repasse" AS valor_liquido  -- ✅ Correto: esta é a origem de valor_liquido
FROM vendas_ml v
LEFT JOIN repasses_ml r ON v."ID Pedido" = r."ID Pedido"
WHERE NOT EXISTS (
    SELECT 1 FROM entradas_financeiras e 
    WHERE e.pedido_id = v."ID Pedido" AND e.tipo = 'ml'
)

            """)
            vendas = cursor.fetchall()

            if not vendas:
                print("✓ Nenhuma nova venda do ML para processar")
                return

            for venda in vendas:
                valor_liquido = float(venda['valor_liquido'] or 0)
                cursor.execute("""
                    INSERT INTO entradas_financeiras (
                        tipo, pedido_id, data_liberacao,
                        valor_total, valor_liquido, 
                        comissoes, taxas, frete, status, origem_conta
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    'ml',
                    venda['pedido_id'],
                    venda['data_repasse'],
                    venda['valor_bruto'],
                    valor_liquido,
                    venda['comissao'],
                    venda['taxas'],
                    venda['frete'],
                    'COMPLETED' if venda['data_repasse'] else 'PENDING',
                    venda['conta'],  # ← Agora corretamente gravado em origem_conta
                ))
            conn.commit()
            print(f"✓ Processadas {len(vendas)} vendas do Mercado Livre (data_liberacao = DATA_REPASSE)")

    except Exception as e:
        print(f"✗ Erro ao processar vendas do ML: {str(e)}")
        raise


async def process_account(account: Dict[str, Any], session: aiohttp.ClientSession) -> None:
    """Processa uma conta individual com tratamento de token."""
    api_url = os.getenv("API_URL")
    if not api_url:
        print(f"URL da API não configurada para conta {account['nome']}")
        return

    success = await fetch_orders_for_account(
        account["access_token"],
        account["seller_id"],
        api_url,
        session
    )

    if not success:
        print(f"Token inválido para conta {account['nome']}, tentando renovar...")
        new_access, new_refresh = await refresh_token(
            account["client_id"],
            account["client_secret"],
            account["refresh_token"],
            api_url,
            session
        )

        if new_access and new_refresh:
            account["access_token"] = new_access
            account["refresh_token"] = new_refresh
            atualizar_env_token(account["nome"], new_access, new_refresh)

            await fetch_orders_for_account(
                new_access,
                account["seller_id"],
                api_url,
                session
            )
        else:
            print(f"Falha ao renovar token para conta {account['nome']}")
async def pipeline_completo() -> None:
    """Executa todo o fluxo de processamento."""
    print("=== INICIANDO PROCESSAMENTO MERCADO LIVRE ===")
    inicializar_banco()

    contas = [
        {
            "nome": "TOYS",
            "client_id": os.getenv("CLIENT_ID_TOYS"),
            "client_secret": os.getenv("CLIENT_SECRET_TOYS"),
            "access_token": os.getenv("ACCESS_TOKEN_TOYS"),
            "refresh_token": os.getenv("REFRESH_TOKEN_TOYS"),
            "seller_id": os.getenv("SELLER_ID_TOYS")
        },
        {
            "nome": "COMERCIAL",
            "client_id": os.getenv("CLIENT_ID_COMERCIAL"),
            "client_secret": os.getenv("CLIENT_SECRET_COMERCIAL"),
            "access_token": os.getenv("ACCESS_TOKEN_COMERCIAL"),
            "refresh_token": os.getenv("REFRESH_TOKEN_COMERCIAL"),
            "seller_id": os.getenv("SELLER_ID_COMERCIAL")
        },
        {
            "nome": "PESCA",
            "client_id": os.getenv("CLIENT_ID_PESCA"),
            "client_secret": os.getenv("CLIENT_SECRET_PESCA"),
            "access_token": os.getenv("ACCESS_TOKEN_PESCA"),
            "refresh_token": os.getenv("REFRESH_TOKEN_PESCA"),
            "seller_id": os.getenv("SELLER_ID_PESCA")
        },
        {
            "nome": "CAMPING",
            "client_id": os.getenv("CLIENT_ID_CAMPING"),
            "client_secret": os.getenv("CLIENT_SECRET_CAMPING"),
            "access_token": os.getenv("ACCESS_TOKEN_CAMPING"),
            "refresh_token": os.getenv("REFRESH_TOKEN_CAMPING"),
            "seller_id": os.getenv("SELLER_ID_CAMPING")
        }
    ]

    async with aiohttp.ClientSession() as session:
        tasks = [process_account(conta, session) for conta in contas]
        await asyncio.gather(*tasks)

    print("Processamento de pedidos concluído. Iniciando pós-processamento...")

    atualizar_traducoes_existentes()
    migrar_para_repasses_ml()
    calcular_colunas_repasses()
    atualizar_data_repasse_ml()
    atualizar_entradas_financeiras_ml()

    print("=== PROCESSAMENTO CONCLUÍDO COM SUCESSO ===")

def padronizar_datas_banco():
        import sqlite3
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            for tabela, campo in [
                ("vendas_ml", "Data da Venda"),
                ("vendas_ml", "Data Liberacao"),
                ("repasses_ml", "Data da Venda"),
                ("repasses_ml", "Data Liberacao"),
                ("repasses_ml", "DATA_REPASSE"),
                ("entradas_financeiras", "data_venda"),
                ("entradas_financeiras", "data_liberacao"),
                ("entradas_financeiras", "data_repasse"),
            ]:
                cursor.execute(f"SELECT rowid, \"{campo}\" FROM {tabela}")
                for rowid, valor in cursor.fetchall():
                    novo = data_br_safe(valor)
                    cursor.execute(f"UPDATE {tabela} SET \"{campo}\" = ? WHERE rowid = ?", (novo, rowid))
            conn.commit()


# --- Ponto de Entrada ---
if __name__ == "__main__":
    asyncio.run(pipeline_completo())
    atualizar_preco_custo_ml()
    padronizar_datas_banco()
