import sqlite3
import logging
import json
import os
import sys
import time
import requests
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

import os

ROOT_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT_DIR, 'grupo_fisgar.db')
ENV_PATH = os.path.join(ROOT_DIR, '.env')



# Configuração do sistema
sys.path.append(os.path.join(ROOT_DIR, 'modulos', 'vendas', 'shopee'))
from pyshopee2 import Client

# Carrega variáveis do ambiente
load_dotenv(ENV_PATH)

# Configurações globais
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
REQUEST_TIMEOUT = 30  # Aumentado para conexões lentas
MAX_RETRIES = 5  # Aumentado para maior resiliência


def get_env_variable(account_type, var_type):
    """Obtém variável de ambiente no formato SHOPEE_NOMEVARIAVEL_CONTA"""
    var_map = {
        'PARTNER_ID': f'SHOPEE_PARTNER_ID_{account_type}',
        'PARTNER_KEY': f'SHOPEE_PARTNER_KEY_{account_type}',
        'SHOP_ID': f'SHOPEE_SHOP_ID_{account_type}',
        'ACCESS_TOKEN': f'SHOPEE_ACCESS_TOKEN_{account_type}',
        'REFRESH_TOKEN': f'SHOPEE_REFRESH_TOKEN_{account_type}'
    }

    var_name = var_map.get(var_type)
    if not var_name:
        raise ValueError(f"Tipo de variável inválido: {var_type}")

    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Variável {var_name} não encontrada no .env")

    return value


def create_shopee_client(account_type):
    """Cria e configura cliente da API Shopee com logs detalhados"""
    print(f"\n🔧 Configurando cliente para conta {account_type}")

    try:
        credentials = {
            'partner_id': int(get_env_variable(account_type, 'PARTNER_ID')),
            'partner_key': get_env_variable(account_type, 'PARTNER_KEY'),
            'shop_id': int(get_env_variable(account_type, 'SHOP_ID')),
            'access_token': get_env_variable(account_type, 'ACCESS_TOKEN'),
            'refresh_token': get_env_variable(account_type, 'REFRESH_TOKEN')
        }

        print(f"✅ Credenciais obtidas para {account_type}")
        print(f"SHOP_ID: {credentials['shop_id']}")
        print(f"ACCESS_TOKEN: {credentials['access_token'][:15]}...")
        print(f"REFRESH_TOKEN: {credentials['refresh_token'][:15]}...")

        client = Client(
            shop_id=credentials['shop_id'],
            partner_id=credentials['partner_id'],
            partner_key=credentials['partner_key'],
            redirect_url="https://google.com",
            access_token=credentials['access_token']
        )
        client.refresh_token = credentials['refresh_token']
        client.account_type = account_type

        return client

    except Exception as e:
        print(f"❌ Falha ao configurar cliente {account_type}: {str(e)}")
        raise


def check_and_update_schema(conn):
    """Verifica e atualiza estrutura do banco de dados de forma robusta"""
    cursor = conn.cursor()

    # Criação da tabela principal
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pedidos (
            buyer_user_id TEXT,
            estimated_shipping_fee REAL,
            actual_shipping_fee REAL,
            item_list TEXT,
            total_amount REAL,
            package_list TEXT,
            order_sn TEXT PRIMARY KEY,
            order_status TEXT,
            model_quantity INTEGER,
            shipping_carrier TEXT,
            item_name TEXT,
            model_discounted_price REAL,
            account_type TEXT,
            item_sku TEXT,
            model_sku TEXT,
            create_time TEXT,
            Data_Entregue TEXT
        )
    ''')

    # Verificação de colunas faltantes
    cursor.execute("PRAGMA table_info(pedidos)")
    existing_columns = {col[1] for col in cursor.fetchall()}
    required_columns = {
        'buyer_user_id', 'estimated_shipping_fee', 'actual_shipping_fee',
        'item_list', 'total_amount', 'package_list', 'order_sn',
        'order_status', 'model_quantity', 'shipping_carrier',
        'item_name', 'model_discounted_price', 'account_type',
        'item_sku', 'model_sku', 'create_time', 'Data_Entregue'
    }

    for column in required_columns - existing_columns:
        try:
            cursor.execute(f'ALTER TABLE pedidos ADD COLUMN {column} TEXT')
            print(f"➕ Coluna {column} adicionada")
        except sqlite3.OperationalError:
            pass  # Coluna já existe

    conn.commit()


def get_last_create_time():
    """Retorna timestamp de 60 dias atrás com timezone UTC"""
    return int((datetime.now(timezone.utc) - timedelta(days=60)).timestamp())


def serialize_field(field):
    """Serializa campos complexos para JSON de forma segura"""
    if field is None:
        return ""
    if isinstance(field, (dict, list)):
        try:
            return json.dumps(field, ensure_ascii=False)
        except:
            return ""
    return str(field)


def format_timestamp(timestamp):
    """Formata timestamp para string ISO 8601 com timezone"""
    try:
        return datetime.fromtimestamp(int(timestamp), timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    except:
        return "1970-01-01 00:00:00"  # Valor padrão para timestamps inválidos


def refresh_tokens(client):
    """Atualiza tokens de acesso com tratamento completo"""
    print(f"\n🔄 Atualizando tokens para {client.account_type}")

    try:
        timestamp = int(time.time())
        path = "/api/v2/auth/access_token/get"
        base_string = f"{client.partner_id}{path}{timestamp}"

        signature = hmac.new(
            client.partner_key.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        response = requests.post(
            "https://partner.shopeemobile.com/api/v2/auth/access_token/get",
            headers={"Content-Type": "application/json"},
            json={
                "refresh_token": client.refresh_token,
                "partner_id": client.partner_id,
                "shop_id": client.shop_id
            },
            params={
                "partner_id": client.partner_id,
                "timestamp": timestamp,
                "sign": signature,
                "shop_id": client.shop_id
            },
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code != 200:
            raise Exception(f"Status {response.status_code}: {response.text}")

        data = response.json()
        if 'access_token' not in data or 'refresh_token' not in data:
            raise Exception("Resposta da API inválida")

        print(f"🔑 Novos tokens obtidos para {client.account_type}:")
        print(f"Access Token: {data['access_token'][:15]}...")
        print(f"Refresh Token: {data['refresh_token'][:15]}...")

        # Atualiza arquivo .env mantendo formatação
        with open(ENV_PATH, 'r+') as f:
            lines = f.readlines()
            f.seek(0)

            for line in lines:
                if line.startswith(f"SHOPEE_ACCESS_TOKEN_{client.account_type}="):
                    f.write(f"SHOPEE_ACCESS_TOKEN_{client.account_type}={data['access_token']}\n")
                elif line.startswith(f"SHOPEE_REFRESH_TOKEN_{client.account_type}="):
                    f.write(f"SHOPEE_REFRESH_TOKEN_{client.account_type}={data['refresh_token']}\n")
                else:
                    f.write(line)
            f.truncate()

        # Atualiza cliente
        client.access_token = data['access_token']
        client.refresh_token = data['refresh_token']

        return True

    except Exception as e:
        print(f"❌ Falha na atualização de tokens: {str(e)}")
        return False


def fetch_orders(client, last_create_time):
    """Busca pedidos com tratamento robusto de erros"""
    orders = []
    end_time = int(datetime.now().timestamp())
    time_from = last_create_time
    retry_count = 0

    print(f"\n🔍 Buscando pedidos de {client.account_type}...")

    while time_from < end_time and retry_count < MAX_RETRIES:
        try:
            time_to = min(time_from + (15 * 86400), end_time)
            print(f"⏳ Período: {format_timestamp(time_from)} até {format_timestamp(time_to)}")

            # Busca lista de pedidos
            orders_response = client.order.get_order_list(
                time_range_field="create_time",
                time_from=time_from,
                time_to=time_to,
                page_size=100,  # Aumentado para melhor performance
                timeout=REQUEST_TIMEOUT
            )

            if 'error' in orders_response:
                if orders_response['error'] in ['error_auth', 'error_token']:
                    if refresh_tokens(client):
                        continue  # Repete com novos tokens
                    else:
                        retry_count += 1
                        time.sleep(5)
                        continue

            if 'response' not in orders_response or not orders_response['response'].get('order_list'):
                time_from = time_to
                continue

            # Obtém detalhes dos pedidos
            orders_sn = [o['order_sn'] for o in orders_response['response']['order_list']]
            details = client.order.get_order_detail(
                order_sn_list=",".join(orders_sn),
                response_optional_fields=",".join([
                    "buyer_user_id", "estimated_shipping_fee", "actual_shipping_fee",
                    "item_list", "total_amount", "package_list", "order_status", "create_time"
                ]),
                timeout=REQUEST_TIMEOUT
            )

            if 'response' in details:
                orders.extend(details['response']['order_list'])
                print(f"📦 {len(details['response']['order_list'])} pedidos encontrados")

            time_from = time_to
            retry_count = 0  # Reset do contador após sucesso

        except requests.exceptions.RequestException as e:
            print(f"⚠️ Erro de conexão: {str(e)}")
            retry_count += 1
            time.sleep(10)
        except Exception as e:
            print(f"⚠️ Erro inesperado: {str(e)}")
            retry_count += 1
            time.sleep(5)

    print(f"✅ Total de pedidos obtidos: {len(orders)}")
    return orders


def insert_orders(orders, conn, account_type):
    """Insere pedidos no banco de dados com validação completa"""
    if not orders:
        print("⚠️ Nenhum pedido para inserir")
        return

    cursor = conn.cursor()
    inserted = 0
    errors = 0

    print(f"\n💾 Inserindo {len(orders)} pedidos no banco...")

    for order in orders:
        try:
            # Validação básica
            if not order.get('order_sn') or not order.get('create_time'):
                errors += 1
                continue

            # Verifica se pedido já existe
            cursor.execute("SELECT 1 FROM pedidos WHERE order_sn = ?", (order['order_sn'],))
            if cursor.fetchone():
                continue

            # Prepara dados
            order_data = {
                'order_sn': order.get('order_sn'),
                'create_time': format_timestamp(order.get('create_time')),
                'order_status': order.get('order_status', ''),
                'data_entregue': None
            }

            if order_data['order_status'] == 'COMPLETED':
                delivery_date = datetime.strptime(order_data['create_time'], "%Y-%m-%d %H:%M:%S") + timedelta(days=8)
                order_data['data_entregue'] = delivery_date.strftime("%Y-%m-%d %H:%M:%S")

            # Insere pedido
            cursor.execute('''
                INSERT INTO pedidos VALUES (
                    ?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,?,?,?
                )
            ''', (
                order.get('buyer_user_id', ''),
                order.get('estimated_shipping_fee', 0),
                order.get('actual_shipping_fee', 0),
                serialize_field(order.get('item_list', [])),
                order.get('total_amount', 0),
                serialize_field(order.get('package_list', [])),
                order_data['order_sn'],
                order_data['order_status'],
                order.get('model_quantity', 0),
                order.get('shipping_carrier', ''),
                order.get('item_name', ''),
                order.get('model_discounted_price', 0),
                account_type,
                order.get('item_sku', ''),
                order.get('model_sku', ''),
                order_data['create_time'],
                order_data['data_entregue']
            ))
            inserted += 1

        except Exception as e:
            errors += 1
            print(f"⚠️ Erro no pedido {order.get('order_sn', '?')}: {str(e)}")

    conn.commit()
    print(f"✅ {inserted} pedidos inseridos | ❌ {errors} erros")


def update_completed_orders(conn):
    """Atualiza datas de entrega para pedidos completos"""
    cursor = conn.cursor()
    updated = 0

    print("\n🔄 Atualizando pedidos completos...")

    cursor.execute('''
        SELECT order_sn, create_time 
        FROM pedidos 
        WHERE order_status = 'COMPLETED' 
        AND Data_Entregue IS NULL
    ''')

    for order_sn, create_time in cursor.fetchall():
        try:
            if not create_time:
                continue

            delivery_date = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S") + timedelta(days=8)
            cursor.execute('''
                UPDATE pedidos 
                SET Data_Entregue = ? 
                WHERE order_sn = ?
            ''', (delivery_date.strftime("%Y-%m-%d %H:%M:%S"), order_sn))
            updated += 1

        except Exception as e:
            print(f"⚠️ Erro ao atualizar pedido {order_sn}: {str(e)}")

    conn.commit()
    print(f"✅ {updated} pedidos atualizados")


def main():
    """Função principal com tratamento completo de erros"""
    print("\n" + "=" * 50)
    print("🚀 INICIANDO PROCESSAMENTO SHOPEE")
    print("=" * 50 + "\n")

    conn = None
    try:
        # Conexão com banco de dados
        conn = sqlite3.connect(DB_PATH)
        check_and_update_schema(conn)

        # Processa cada conta
        for conta in ["COMERCIAL", "TOYS"]:
            try:
                print("\n" + "=" * 50)
                print(f"🛍️  PROCESSANDO CONTA {conta}")
                print("=" * 50)

                # Configura cliente
                client = create_shopee_client(conta)

                # Busca pedidos
                pedidos = fetch_orders(client, get_last_create_time())

                # Insere no banco
                insert_orders(pedidos, conn, conta)

            except Exception as e:
                print(f"\n❌ ERRO NA CONTA {conta}: {str(e)}")
                continue

        # Atualiza pedidos completos
        update_completed_orders(conn)

    except Exception as e:
        print(f"\n❌❌ ERRO CRÍTICO: {str(e)}")
    finally:
        if conn:
            conn.close()

    print("\n" + "=" * 50)
    print("🏁 PROCESSAMENTO CONCLUÍDO")
    print("=" * 50)


if __name__ == '__main__':
    main()