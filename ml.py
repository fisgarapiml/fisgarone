import sqlite3
import aiohttp
import asyncio
from dotenv import load_dotenv, set_key
import os
from datetime import datetime, timedelta

# Carregar variáveis do arquivo .env
load_dotenv()

# Inicializar banco SQLite com as colunas corretas
def inicializar_banco():
    print("Inicializando o banco de dados...")
    with sqlite3.connect('grupo_fisgar.db') as conn:  # Alterado para vendas.db
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

# Função para atualizar o arquivo .env com os novos tokens
def atualizar_env_token(account_name, new_access_token, new_refresh_token):
    # Atualiza o arquivo .env com os novos tokens
    set_key('.env', f'ACCESS_TOKEN_{account_name}', new_access_token)
    set_key('.env', f'REFRESH_TOKEN_{account_name}', new_refresh_token)

# Função assíncrona para obter o novo token com o refresh token
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
                print(f"Erro ao atualizar o token para o client_id {client_id}: {response.status} - {await response.text()}")
                return None, None
    except Exception as e:
        print(f"Erro ao tentar atualizar o token: {e}")
        return None, None

# Função para buscar os custos de envio (shipping_cost e shipping_base_cost)
async def fetch_shipment_costs_and_payments(access_token, shipment_id, api_url, session):
    headers = {"Authorization": f"Bearer {access_token}", "x-format-new": "true"}

    # Definir as URLs para as rotas de custos e pagamentos
    costs_url = f"{api_url}/shipments/{shipment_id}/costs"  # Rota para buscar shipping_base_cost
    payments_url = f"{api_url}/shipments/{shipment_id}/payments"  # Rota para buscar shipping_cost

    try:
        # Buscar os custos do envio (shipping_base_cost)
        async with session.get(costs_url, headers=headers) as response:
            if response.status == 200:
                shipment_costs = await response.json()
                # Garantir que o valor de shipping_base_cost seja extraído corretamente
                shipping_base_cost = float(shipment_costs.get("gross_amount", 0.0))
                print(f"Shipping base cost para shipment_id {shipment_id}: {shipping_base_cost}")
            else:
                print(f"Erro ao buscar custos do envio para {shipment_id}: {response.status} - {await response.text()}")
                return None, None

        # Buscar os pagamentos do envio (shipping_cost)
        async with session.get(payments_url, headers=headers) as response:
            if response.status == 200:
                shipment_payments = await response.json()
                # Verifique se shipment_payments é uma lista não vazia
                if isinstance(shipment_payments, list) and shipment_payments:
                    # Se for uma lista, pegue o primeiro item
                    shipping_cost = float(shipment_payments[0].get("amount", 0.0))  # Pegando o primeiro pagamento
                elif isinstance(shipment_payments, dict):
                    # Caso seja um dicionário, acesse diretamente
                    shipping_cost = float(shipment_payments.get("amount", 0.0))  
                else:
                    shipping_cost = 0.0  # Caso não seja nem lista nem dicionário
                print(f"Shipping cost para shipment_id {shipment_id}: {shipping_cost}")
            else:
                print(f"Erro ao buscar pagamentos do envio para {shipment_id}: {response.status} - {await response.text()}")
                return None, None

        return shipping_cost, shipping_base_cost

    except Exception as e:
        print(f"Erro ao acessar dados de envio e pagamentos: {e}")
        return None, None

# Função para buscar os dados de envio de um shipment_id
async def fetch_shipment(access_token, shipment_id, api_url, session):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{api_url}/shipments/{shipment_id}"

    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                shipment = await response.json()

                # Obtendo os parâmetros de envio
                logistic_type = shipment.get("logistic_type", "Não disponível")
                shipping_mode = shipment.get("shipping_mode", "")
                shipping_base_cost = float(shipment.get("shipping_option", {}).get("base_cost", 0.0))
                shipping_option_cost = float(shipment.get("shipping_option", {}).get("cost", 0.0))
                shipping_order_cost = float(shipment.get("order_cost", 0.0))
                shipping_list_cost = float(shipment.get("shipping_option", {}).get("list_cost", 0.0))
                total_shipping_cost = float(shipment.get("total", 0.0))
                paid_by = shipment.get("costs", [{}])[0].get("paid_by", "unknown")
                status = shipment.get("status", "")
                delivery_status = shipment.get("tracking", {}).get("status", "")
                release_date = shipment.get("date_estimated_delivery", {}).get("date", None)

                # Garantir que release_date seja uma data válida
                if release_date:
                    try:
                        # Converter para o formato de data padrão, se necessário
                        release_date = datetime.strptime(release_date, "%Y-%m-%dT%H:%M:%S")  # Exemplo de formato, ajuste conforme necessário
                        release_date = release_date.strftime("%Y-%m-%d %H:%M:%S")  # Converte para string no formato adequado
                    except ValueError:
                        print(f"Formato inválido de release_date: {release_date}")
                        release_date = None  # Caso ocorra erro, atribui None

                date_created = shipment.get("date_created", "")

                # Buscar custos de envio (shipping_cost e shipping_base_cost) através das novas rotas
                shipping_cost, shipping_base_cost = await fetch_shipment_costs_and_payments(
                    access_token, shipment_id, api_url, session
                )

                # Atualizar os valores com base nos custos obtidos
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
                        "paid_by": paid_by,
                        "status": status,
                        "delivery_status": delivery_status,
                        "release_date": release_date,
                        "date_created": date_created
                    }

                return None
            else:
                print(f"Erro ao buscar envio {shipment_id}: {response.status} - {await response.text()}")
                return None
    except Exception as e:
        print(f"Erro ao tentar acessar o envio: {e}")
        return None

from datetime import datetime, timedelta
from dateutil import parser
import pytz  # Para lidar com fuso horário

# Buscar dados da API do Mercado Livre e salvar no banco
async def buscar_pedidos_e_envios(access_token, seller_id, api_url, session):
    with sqlite3.connect('grupo_fisgar.db') as conn:  # Alterado para vendas.db
        cursor = conn.cursor()

        headers = {"Authorization": f"Bearer {access_token}"}
        offset = 0
        limit = 50  # Limitar a 50 registros
        total = 0

        # Calcular a data de 30 dias atrás (tornando-a aware)
        data_60_dias_antes = datetime.now(pytz.timezone('America/Sao_Paulo')) - timedelta(days=60)  # Usando o fuso horário de SP
        data_60_dias_antes_str = data_60_dias_antes.strftime("%Y-%m-%dT%H:%M:%S%z")  # Formato ISO com fuso horário
        print(f"Buscando pedidos a partir de: {data_60_dias_antes_str}")

        print(f"Iniciando a busca de pedidos para o seller_id: {seller_id}")

        while offset < total or total == 0:
            # Filtrar pedidos para buscar apenas os que foram criados nos últimos 30 dias
            url_pedidos = f"{api_url}/orders/search?seller={seller_id}&date_created.from={data_60_dias_antes_str}&offset={offset}&limit={limit}"
            print(f"URL da requisição: {url_pedidos}")

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

                                # Adicionando data do pedido para registro (data criada)
                                try:
                                    # Usando parser.parse() para lidar com o fuso horário
                                    date_created_obj = parser.parse(date_created)  # Converte a data, incluindo o fuso horário

                                    # Verificando se a data de criação do pedido está dentro do limite de 30 dias
                                    if date_created_obj >= data_60_dias_antes:
                                        cancellations = "cancelled" if pedido.get("status") == "cancelled" else "active"

                                        # Preenchendo os dados de cada item do pedido
                                        for item in pedido.get("order_items", []):
                                            unit_price = float(item.get("unit_price", 0.0))
                                            quantity = int(item.get("quantity", 0))
                                            sale_fee = float(item.get("sale_fee", 0.0))
                                            title = item.get("item", {}).get("title", "")
                                            mlb = item.get("item", {}).get("id", "")
                                            sku = item.get("item", {}).get("seller_sku", "")

                                            # Dados de envio
                                            shipment = pedido.get('shipping', {})  # A chave pode ser 'shipping'
                                            shipment_id = shipment.get('id', "")
                                            buyer_id = pedido.get('buyer', {}).get('id', "")
                                            
                                            # Chama a função para buscar os detalhes do envio
                                            envio_details = await fetch_shipment(access_token, shipment_id, api_url, session)

                                            if envio_details:
                                                print(f"Inserindo pedido {order_id} no banco de dados.")
                                                cursor.execute('''INSERT OR REPLACE INTO vendas_ml (
                                                    order_id, unit_price, quantity, date_created, sale_fee, shipping_cost,
                                                    seller_id, cancellations, title, mlb, sku, shipment_id, buyer_id,
                                                    shipping_mode, shipping_base_cost, shipping_option_cost, shipping_order_cost,
                                                    shipping_list_cost, total_shipping_cost, logistic_type, paid_by, status,
                                                    delivery_status, release_date
                                                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                                                (order_id, unit_price, quantity, date_created, sale_fee, envio_details["total_shipping_cost"],
                                                 seller_id, cancellations, title, mlb, sku, shipment_id, buyer_id,
                                                 envio_details["shipping_mode"], envio_details["shipping_base_cost"],
                                                 envio_details["shipping_option_cost"], envio_details["shipping_order_cost"],
                                                 envio_details["shipping_list_cost"], envio_details["total_shipping_cost"],
                                                 envio_details["logistic_type"], envio_details["paid_by"],
                                                 envio_details["status"], envio_details["delivery_status"],
                                                 envio_details["release_date"]))

                                            conn.commit()

                                except ValueError:
                                    print(f"Data de criação inválida para o pedido {order_id}: {date_created}")
                                    
                        offset += limit
                    else:
                        print(f"Erro ao buscar pedidos: {response.status} - {await response.text()}")
                        break
            except Exception as e:
                print(f"Erro ao buscar pedidos para o Seller ID {seller_id}: {e}")
                break

        conn.commit()


# Função principal assíncrona
async def executar():
    inicializar_banco()

    # Lista de contas com informações completas
    contas = [
        {"nome": "TOYS", "client_id": os.getenv("CLIENT_ID_TOYS"), "client_secret": os.getenv("CLIENT_SECRET_TOYS"), "access_token": os.getenv("ACCESS_TOKEN_TOYS"), "refresh_token": os.getenv("REFRESH_TOKEN_TOYS"), "seller_id": os.getenv("SELLER_ID_TOYS")},
        {"nome": "COMERCIAL", "client_id": os.getenv("CLIENT_ID_COMERCIAL"), "client_secret": os.getenv("CLIENT_SECRET_COMERCIAL"), "access_token": os.getenv("ACCESS_TOKEN_COMERCIAL"), "refresh_token": os.getenv("REFRESH_TOKEN_COMERCIAL"), "seller_id": os.getenv("SELLER_ID_COMERCIAL")},
        {"nome": "PESCA", "client_id": os.getenv("CLIENT_ID_PESCA"), "client_secret": os.getenv("CLIENT_SECRET_PESCA"), "access_token": os.getenv("ACCESS_TOKEN_PESCA"), "refresh_token": os.getenv("REFRESH_TOKEN_PESCA"), "seller_id": os.getenv("SELLER_ID_PESCA")},
        {"nome": "CAMPING", "client_id": os.getenv("CLIENT_ID_CAMPING"), "client_secret": os.getenv("CLIENT_SECRET_CAMPING"), "access_token": os.getenv("ACCESS_TOKEN_CAMPING"), "refresh_token": os.getenv("REFRESH_TOKEN_CAMPING"), "seller_id": os.getenv("SELLER_ID_CAMPING")},
    ]

    api_url = os.getenv("API_URL")

    async with aiohttp.ClientSession() as session:
        tasks = []

        # Cria uma tarefa para cada conta
        for conta in contas:
            if conta["access_token"] and conta["client_id"]:  # Verificando client_id
                print(f"Verificando se o token está válido para a conta {conta['nome']}...")

                # Atualiza o token antes de buscar pedidos
                new_access_token, new_refresh_token = await refresh_token(conta["client_id"], conta["client_secret"], conta["refresh_token"], api_url, session)

                if new_access_token and new_refresh_token:
                    # Atualiza o arquivo .env com os novos tokens
                    atualizar_env_token(conta['nome'], new_access_token, new_refresh_token)
                    print(f"Tokens atualizados para a conta {conta['nome']}.")
                    conta["access_token"] = new_access_token
                    conta["refresh_token"] = new_refresh_token

                print(f"Buscando pedidos e envios para a conta {conta['nome']} (Seller ID: {conta['seller_id']})...")
                tasks.append(buscar_pedidos_e_envios(conta["access_token"], conta["seller_id"], api_url, session))
            else:
                print(f"Credenciais não encontradas para a conta {conta['nome']}. Verifique o arquivo .env.")

        # Executa todas as tarefas de forma assíncrona
        await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(executar())
