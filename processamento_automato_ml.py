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
            "Preço Custo ML": round(preco_custo_ml, 2),
            "Custo Total Calculado": round(custo_total_calculado, 2),
            "Aliquota (%)": aliquota_percent,
            "Imposto R$": round(imposto_r, 2),
            "Frete Comprador": round(frete_comprador, 2),
            "Frete Seller": round(frete_seller, 2),
            "Custo Operacional": round(custo_operacional, 2),
            "Total Custo Operacional": round(total_custo_operacional, 2),
            "MC Total": round(mc_total, 2),
            "Custo Fixo": round(custo_fixo, 2),
            "Lucro Real": round(lucro_real, 2),
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


def migrar_para_repasses_ml():
    print("[PASSO 3] Migrando dados essenciais para repasses_ml...")

    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Verifica se as colunas necessárias existem em vendas_ml
        cursor.execute("PRAGMA table_info(vendas_ml)")
        vendas_cols = [c[1] for c in cursor.fetchall()]
        required = [
            "ID Pedido", "Data da Venda", "Conta", "Preco Unitario", "Quantidade",
            "Taxa Fixa ML", "Comissoes", "Custo Lista Frete", "Data Liberacao"
        ]
        missing = [c for c in required if c not in vendas_cols]
        if missing:
            print("❌ Faltando colunas na vendas_ml:", missing)
            return

        # Migra os dados aplicando a regra do frete_seller
        cursor.execute('''
            INSERT OR REPLACE INTO repasses_ml (
                "ID Pedido", "Data da Venda", "Conta", "Preco Unitario", "Quantidade",
                "Taxa Fixa ML", "Comissoes", "Frete Seller", "Data Liberacao"
            )
            SELECT
                "ID Pedido", "Data da Venda", "Conta", "Preco Unitario", "Quantidade",
                "Taxa Fixa ML", "Comissoes",
                CASE WHEN "Preco Unitario" >= 79 THEN "Custo Lista Frete" ELSE 0 END AS "Frete Seller",
                "Data Liberacao"
            FROM vendas_ml
            WHERE "ID Pedido" IS NOT NULL
        ''')
        conn.commit()

    print("Migração finalizada: repasses_ml alimentado com frete_seller conforme regra dos R$79,00.")


def calcular_colunas_repasses() -> None:
    """Calcula colunas derivadas na tabela repasses_ml."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE repasses_ml SET
                "Total da Venda" = ROUND(COALESCE("Preco Unitario", 0) * COALESCE("Quantidade", 0), 2),
                "Total Custo" = ROUND(COALESCE("Taxa Fixa ML", 0) + COALESCE("Comissoes", 0) + COALESCE("Frete Seller", 0), 2),
                "Valor do Repasse" = ROUND(COALESCE("Total da Venda", 0) - COALESCE("Total Custo", 0), 2)
        ''')
        conn.commit()

def atualizar_data_repasse_ml() -> None:
    """Calcula a data de repasse baseada no tipo de logística."""
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


def atualizar_entradas_financeiras_ml() -> None:
    """Atualiza a tabela entradas_financeiras evitando duplicações."""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()

        # Criar tabela temporária para evitar duplicação
        cursor.execute('''
            CREATE TEMPORARY TABLE temp_entradas AS
            SELECT DISTINCT
                'ml' as tipo,
                "ID Pedido" as pedido_id,
                "Data da Venda" as data_venda,
                "Data Liberacao" as data_liberacao,
                "Preco Unitario" * "Quantidade" as valor_total,
                ("Preco Unitario" * "Quantidade") - ("Taxa Fixa ML" + "Comissoes" + "Frete Seller") as valor_liquido,
                "Comissoes" as comissoes,
                "Taxa Fixa ML" as taxas,
                "Frete Seller" as frete,
                CASE WHEN "Data Liberacao" IS NOT NULL AND "Data Liberacao" != '' 
                     THEN 'Recebido' ELSE 'Pendente' END as status,
                "Conta" as origem_conta,
                '' as observacoes,
                CASE
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
                END as data_repasse
            FROM vendas_ml
            WHERE "ID Pedido" IS NOT NULL
        ''')

        # Limpar a tabela principal
        cursor.execute('DELETE FROM entradas_financeiras WHERE tipo = "ml"')

        # Inserir os dados da temporária
        cursor.execute('''
            INSERT INTO entradas_financeiras (
                tipo, pedido_id, data_venda, data_liberacao,
                valor_total, valor_liquido, comissoes, taxas, frete,
                status, origem_conta, observacoes, data_repasse
            )
            SELECT * FROM temp_entradas
        ''')

        # Limpar a tabela temporária
        cursor.execute('DROP TABLE temp_entradas')
        conn.commit()
# --- Pipeline Principal ---
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

# --- Ponto de Entrada ---
if __name__ == "__main__":
    asyncio.run(pipeline_completo())