import sqlite3
import aiohttp
import asyncio
from dotenv import load_dotenv, set_key
import os
from dateutil import parser

# Carregar variáveis do arquivo .env
load_dotenv()

db_path = r"C:\fisgarone\grupo_fisgar.db"  # ajuste se necessário
api_url = os.getenv("API_URL")

def atualizar_env_token(account_name, new_access_token, new_refresh_token):
    set_key('.env', f'ACCESS_TOKEN_{account_name}', new_access_token)
    set_key('.env', f'REFRESH_TOKEN_{account_name}', new_refresh_token)

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
                print(f"Erro ao atualizar token para {client_id}: {response.status} - {await response.text()}")
                return None, None
    except Exception as e:
        print(f"Erro ao atualizar token: {e}")
        return None, None

async def fetch_billing_details(access_token, order_id, api_url, session):
    headers = {"Authorization": f"Bearer {access_token}"}
    url = f"{api_url}/billing/integration/group/ML/order/details?order_ids={order_id}"
    try:
        async with session.get(url, headers=headers) as response:
            if response.status == 200:
                data = await response.json()
                results = data.get('results', [])
                if results:
                    order_data = results[0]
                    # Quem pagou o frete
                    paid_by = "seller"
                    for detail in order_data.get('details', []):
                        if detail.get('marketplace_info', {}).get('marketplace') == 'SHIPPING':
                            receiver_cost = detail.get('shipping_info', {}).get('receiver_shipping_cost')
                            if receiver_cost is not None and float(receiver_cost) == 0:
                                paid_by = "seller"
                            else:
                                paid_by = "buyer"
                    # Data de liberação
                    release_date = None
                    payment_info = order_data.get('payment_info', [])
                    if payment_info:
                        release_date = payment_info[0].get('money_release_date')
                        if release_date:
                            try:
                                release_date = parser.parse(release_date).strftime("%Y-%m-%d %H:%M:%S")
                            except Exception:
                                release_date = None
                    return paid_by, release_date
                else:
                    return None, None
            elif response.status == 403:
                print(f"403 proibido para pedido {order_id}.")
                return None, None
            else:
                print(f"Erro billing para pedido {order_id}: {response.status}")
                return None, None
    except Exception as e:
        print(f"Erro processando pedido {order_id}: {e}")
        return None, None

async def atualizar_campos_antigos():
    contas = [
        {"nome": "TOYS", "client_id": os.getenv("CLIENT_ID_TOYS"), "client_secret": os.getenv("CLIENT_SECRET_TOYS"),
         "access_token": os.getenv("ACCESS_TOKEN_TOYS"), "refresh_token": os.getenv("REFRESH_TOKEN_TOYS"),
         "seller_id": os.getenv("SELLER_ID_TOYS")},
        {"nome": "COMERCIAL", "client_id": os.getenv("CLIENT_ID_COMERCIAL"), "client_secret": os.getenv("CLIENT_SECRET_COMERCIAL"),
         "access_token": os.getenv("ACCESS_TOKEN_COMERCIAL"), "refresh_token": os.getenv("REFRESH_TOKEN_COMERCIAL"),
         "seller_id": os.getenv("SELLER_ID_COMERCIAL")},
        {"nome": "PESCA", "client_id": os.getenv("CLIENT_ID_PESCA"), "client_secret": os.getenv("CLIENT_SECRET_PESCA"),
         "access_token": os.getenv("ACCESS_TOKEN_PESCA"), "refresh_token": os.getenv("REFRESH_TOKEN_PESCA"),
         "seller_id": os.getenv("SELLER_ID_PESCA")},
        {"nome": "CAMPING", "client_id": os.getenv("CLIENT_ID_CAMPING"), "client_secret": os.getenv("CLIENT_SECRET_CAMPING"),
         "access_token": os.getenv("ACCESS_TOKEN_CAMPING"), "refresh_token": os.getenv("REFRESH_TOKEN_CAMPING"),
         "seller_id": os.getenv("SELLER_ID_CAMPING")},
    ]

    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT "ID Pedido", "Conta" FROM vendas_ml
            WHERE ("Data Liberacao" IS NULL OR "Data Liberacao" = '')
               OR ("Pago Por" IS NULL OR "Pago Por" = '')
        """)
        pedidos = cursor.fetchall()

    if not pedidos:
        print("Nenhum pedido antigo para atualizar.")
        return

    print(f"Total de pedidos para atualizar: {len(pedidos)}")

    async with aiohttp.ClientSession() as session:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            for order_id, conta_nome in pedidos:
                conta = next((c for c in contas if c["nome"] == conta_nome), None)
                if not conta:
                    print(f"Conta '{conta_nome}' não encontrada para pedido {order_id}.")
                    continue

                # Atualizar token antes de consumir API
                new_access_token, new_refresh_token = await refresh_token(
                    conta["client_id"], conta["client_secret"], conta["refresh_token"], api_url, session
                )
                if new_access_token:
                    conta["access_token"] = new_access_token
                    conta["refresh_token"] = new_refresh_token
                    atualizar_env_token(conta["nome"], new_access_token, new_refresh_token)
                else:
                    print(f"Não foi possível atualizar o token da conta {conta['nome']} - pedido {order_id}")
                    continue

                paid_by, release_date = await fetch_billing_details(conta["access_token"], order_id, api_url, session)

                if paid_by is None and release_date is None:
                    print(f"Pedido {order_id} não atualizado (erro 403, acesso negado ou não encontrado).")
                    continue

                cursor.execute("""
                    UPDATE vendas_ml
                    SET "Pago Por" = COALESCE(?, "Pago Por"),
                        "Data Liberacao" = COALESCE(?, "Data Liberacao")
                    WHERE "ID Pedido" = ?
                """, (paid_by, release_date, order_id))
                print(f"Atualizado pedido {order_id}: Pago Por={paid_by}, Data Liberacao={release_date}")
            conn.commit()

if __name__ == "__main__":
    asyncio.run(atualizar_campos_antigos())
