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
from flask import Blueprint, jsonify

# Importa o cliente Shopee ajustado
from modulos.shopee.pyshopee2 import Client

load_dotenv()

shopee_importador_bp = Blueprint('shopee_importador_bp', __name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
REQUEST_TIMEOUT = 20
MAX_RETRIES = 3

def get_env_variable(var_name):
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Variável {var_name} não encontrada no .env")
    return value

def create_shopee_client(shop_id, partner_id, partner_key, access_token, refresh_token, account_type):
    client = Client(
        shop_id=shop_id,
        partner_id=partner_id,
        partner_key=partner_key,
        redirect_url="https://google.com",
        access_token=access_token
    )
    client.refresh_token = refresh_token
    client.account_type = account_type
    client.partner_id = partner_id
    client.partner_key = partner_key
    return client

def check_and_update_schema(conn):
    cursor = conn.cursor()
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
    conn.commit()

def get_last_create_time():
    return int((datetime.now(timezone.utc) - timedelta(days=60)).timestamp())

def format_timestamp(ts):
    return datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def serialize_field(field):
    if isinstance(field, (dict, list)):
        return json.dumps(field, ensure_ascii=False)
    return str(field) if field else ""

def refresh_tokens(client):
    try:
        timestamp = int(time.time())
        path = "/api/v2/auth/access_token/get"
        base_string = f"{client.partner_id}{path}{timestamp}"

        signature = hmac.new(
            client.partner_key.encode('utf-8'),
            base_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        headers = {"Content-Type": "application/json"}
        params = {
            "partner_id": client.partner_id,
            "timestamp": timestamp,
            "sign": signature,
            "shop_id": client.shop_id
        }

        data = {
            "refresh_token": client.refresh_token,
            "partner_id": client.partner_id,
            "shop_id": client.shop_id
        }

        response = requests.post(
            "https://partner.shopeemobile.com/api/v2/auth/access_token/get",
            json=data,
            headers=headers,
            params=params,
            timeout=REQUEST_TIMEOUT
        )

        if response.status_code == 200:
            new_tokens = response.json()
            client.access_token = new_tokens['access_token']
            client.refresh_token = new_tokens['refresh_token']
            logging.info(f"Tokens atualizados para {client.account_type}")
            return True

        logging.error(f"Falha na renovação: {response.status_code} - {response.text}")
        return False

    except Exception as e:
        logging.error(f"Erro na renovação: {str(e)}", exc_info=True)
        return False

def fetch_orders(client, last_create_time):
    orders = []
    end_time = int(datetime.now().timestamp())
    time_from = last_create_time

    while time_from < end_time:
        time_to = min(time_from + (15 * 86400), end_time)
        logging.info(f"Buscando pedidos de {format_timestamp(time_from)} a {format_timestamp(time_to)}")

        has_more = True
        next_cursor = 0
        retries = 0

        while has_more and retries < MAX_RETRIES:
            try:
                resp_json = client.order.get_order_list(
                    time_range_field="create_time",
                    time_from=time_from,
                    time_to=time_to,
                    page_size=50,
                    cursor=next_cursor,
                    timeout=REQUEST_TIMEOUT
                )

                if 'error' in resp_json and resp_json.get('error') in ['error_auth', 'error_token']:
                    if refresh_tokens(client):
                        continue
                    retries += 1
                    continue

                if 'response' not in resp_json:
                    logging.warning("Resposta da API inválida")
                    return []

                order_list = resp_json['response'].get('order_list', [])
                if not order_list:
                    break

                orders_sn = [o['order_sn'] for o in order_list]
                detalhes = client.order.get_order_detail(
                    order_sn_list=','.join(orders_sn),
                    response_optional_fields=','.join([
                        "buyer_user_id", "estimated_shipping_fee",
                        "actual_shipping_fee", "item_list", "total_amount",
                        "package_list", "order_sn", "order_status", "create_time"
                    ])
                )

                if 'response' in detalhes:
                    orders.extend(detalhes['response']['order_list'])

                has_more = resp_json['response']['more']
                next_cursor = int(resp_json['response']['next_cursor']) if has_more else 0

            except requests.exceptions.RequestException as e:
                retries += 1
                logging.error(f"Erro de conexão ({retries}/{MAX_RETRIES}): {str(e)}")
                time.sleep(5)

        time_from = time_to

    return orders

def insert_orders(orders, conn, account_type):
    cursor = conn.cursor()
    for order in orders:
        try:
            order_sn = order.get('order_sn')
            create_time = order.get('create_time')
            order_status = order.get('order_status', '')

            if not order_sn or not create_time:
                continue

            if cursor.execute("SELECT 1 FROM pedidos WHERE order_sn = ?", (order_sn,)).fetchone():
                continue

            create_time_str = format_timestamp(create_time)
            data_entregue = None
            if order_status == 'COMPLETED':
                create_date = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S")
                data_entregue = (create_date + timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")

            valores = (
                order.get('buyer_user_id', ''),
                order.get('estimated_shipping_fee', 0),
                order.get('actual_shipping_fee', 0),
                serialize_field(order.get('item_list', [])),
                order.get('total_amount', 0),
                serialize_field(order.get('package_list', [])),
                order_sn,
                order_status,
                order.get('model_quantity', 0),
                order.get('shipping_carrier', ''),
                order.get('item_name', ''),
                order.get('model_discounted_price', 0),
                account_type,
                order.get('item_sku', ''),
                order.get('model_sku', ''),
                create_time_str,
                data_entregue
            )

            cursor.execute('''
                INSERT INTO pedidos VALUES (
                    ?,?,?,?,?,?,?,?,?,?,
                    ?,?,?,?,?,?,?
                )
            ''', valores)

        except Exception as e:
            logging.error(f"Erro no pedido {order.get('order_sn', '')}: {str(e)}")

    conn.commit()

def main():
    conn = sqlite3.connect('grupo_fisgar.db')
    check_and_update_schema(conn)

    for conta in ["COMERCIAL", "TOYS"]:
        try:
            client = create_shopee_client(
                shop_id=int(get_env_variable(f"SHOP_ID_{conta}")),
                partner_id=int(get_env_variable(f"PARTNER_ID_{conta}")),
                partner_key=get_env_variable(f"PARTNER_KEY_{conta}"),
                access_token=get_env_variable(f"ACCESS_TOKEN_{conta}"),
                refresh_token=get_env_variable(f"REFRESH_TOKEN_{conta}"),
                account_type=conta
            )

            pedidos = fetch_orders(client, get_last_create_time())
            insert_orders(pedidos, conn, conta)
            logging.info(f"Conta {conta} processada com sucesso")

        except Exception as e:
            logging.error(f"Erro na conta {conta}: {str(e)}")

    conn.close()

@shopee_importador_bp.route('/executar')
def executar_importador_shopee():
    try:
        main()
        return jsonify({"status": "Importação Shopee concluída com sucesso."})
    except Exception as e:
        return jsonify({"status": "Erro na importação", "erro": str(e)}), 500

if __name__ == '__main__':
    main()
