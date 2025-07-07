import os
import sys
import sqlite3
import logging
import json
import time
import requests
import hmac
import hashlib
import pandas as pd
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
from pyshopee2 import Client

# === CONFIGURAÇÕES ===
DB_PATH = r"C:\fisgarone\fisgarone.db"
ENV_PATH = r"C:\fisgarone\.env"

print("DB Exists?", os.path.exists(DB_PATH))
print("ENV Exists?", os.path.exists(ENV_PATH))

# Carrega variáveis do .env (só precisa fazer uma vez no topo)
load_dotenv(ENV_PATH)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
REQUEST_TIMEOUT = 20
MAX_RETRIES = 3

def atualizar_entradas_financeiras(cursor):
    """
    Atualiza ou insere as entradas financeiras a partir da tabela de repasses_shopee.
    """
    cursor.execute("""
        SELECT PEDIDO_ID, DATA, DATA_ENTREGA, VALOR_TOTAL, COMISSAO_UNITARIA, TAXA_FIXA, STATUS_PEDIDO
        FROM repasses_shopee
    """)
    for row in cursor.fetchall():
        cursor.execute("""
            INSERT INTO entradas_financeiras 
            (tipo, pedido_id, data_venda, data_liberacao, valor_total, comissoes, taxas, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(pedido_id, tipo) DO UPDATE SET
                data_venda=excluded.data_venda,
                data_liberacao=excluded.data_liberacao,
                valor_total=excluded.valor_total,
                comissoes=excluded.comissoes,
                taxas=excluded.taxas,
                status=excluded.status
        """, (
            'shopee',
            row[0],    # pedido_id
            row[1],    # data_venda
            row[2],    # data_liberacao
            row[3],    # valor_total
            row[4],    # comissoes
            row[5],    # taxas
            row[6],    # status
        ))

def get_env_variable(account_type, var_type):
    var_map = {
        'PARTNER_ID': f'SHOPEE_PARTNER_ID_{account_type}',
        'PARTNER_KEY': f'SHOPEE_PARTNER_KEY_{account_type}',
        'SHOP_ID': f'SHOPEE_SHOP_ID_{account_type}',
        'ACCESS_TOKEN': f'SHOPEE_ACCESS_TOKEN_{account_type}',
        'REFRESH_TOKEN': f'SHOPEE_REFRESH_TOKEN_{account_type}'
    }
    var_name = var_map[var_type]
    value = os.getenv(var_name)
    if not value:
        raise ValueError(f"Variável {var_name} não encontrada no .env")
    return value

def create_shopee_client(account_type):
    client = Client(
        shop_id=int(get_env_variable(account_type, 'SHOP_ID')),
        partner_id=int(get_env_variable(account_type, 'PARTNER_ID')),
        partner_key=get_env_variable(account_type, 'PARTNER_KEY'),
        redirect_url="https://google.com",
        access_token=get_env_variable(account_type, 'ACCESS_TOKEN')
    )
    client.refresh_token = get_env_variable(account_type, 'REFRESH_TOKEN')
    client.account_type = account_type
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

def serialize_field(field):
    if isinstance(field, (dict, list)):
        return json.dumps(field, ensure_ascii=False)
    return str(field) if field else ""

def format_timestamp(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

# ===============================
# TOKENS SHOPEE - BLOCO ROBUSTO
# ===============================
def generate_signature(partner_id, path, timestamp, partner_key):
    base_string = f"{partner_id}{path}{timestamp}"
    return hmac.new(
        partner_key.encode(),
        base_string.encode(),
        hashlib.sha256
    ).hexdigest()

def update_env_file(new_tokens):
    with open(ENV_PATH, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    for account, tokens in new_tokens.items():
        for idx, line in enumerate(lines):
            if line.startswith(f"SHOPEE_ACCESS_TOKEN_{account}="):
                lines[idx] = f'SHOPEE_ACCESS_TOKEN_{account}={tokens["access_token"]}\n'
            elif line.startswith(f"SHOPEE_REFRESH_TOKEN_{account}="):
                lines[idx] = f'SHOPEE_REFRESH_TOKEN_{account}={tokens["refresh_token"]}\n'
    with open(ENV_PATH, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def refresh_tokens(account_type, partner_id, partner_key, shop_id, refresh_token):
    try:
        timestamp = int(time.time())
        path = "/api/v2/auth/access_token/get"
        signature = generate_signature(partner_id, path, timestamp, partner_key)
        headers = {"Content-Type": "application/json"}
        params = {
            "partner_id": int(partner_id),
            "timestamp": timestamp,
            "sign": signature
        }
        data = {
            "refresh_token": refresh_token,
            "partner_id": int(partner_id),
            "shop_id": int(shop_id)
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
            access_token = new_tokens.get("access_token")
            refresh_token = new_tokens.get("refresh_token")
            if access_token and refresh_token:
                os.environ[f"SHOPEE_ACCESS_TOKEN_{account_type}"] = access_token
                os.environ[f"SHOPEE_REFRESH_TOKEN_{account_type}"] = refresh_token
                update_env_file({
                    account_type: {
                        "access_token": access_token,
                        "refresh_token": refresh_token
                    }
                })
                logging.info(f"Tokens atualizados para {account_type}")
                return access_token, refresh_token
            else:
                logging.error(f"Resposta sem tokens para {account_type}: {new_tokens}")
                return None, None
        else:
            logging.error(f"Falha na renovação [{account_type}]: {response.status_code} - {response.text}")
            return None, None
    except Exception as e:
        logging.error(f"Erro na renovação [{account_type}]: {str(e)}", exc_info=True)
        return None, None

def atualizar_todos_tokens():
    accounts = {
        "COMERCIAL": {
            "partner_id": os.getenv("SHOPEE_PARTNER_ID_COMERCIAL"),
            "partner_key": os.getenv("SHOPEE_PARTNER_KEY_COMERCIAL"),
            "shop_id": os.getenv("SHOPEE_SHOP_ID_COMERCIAL"),
            "refresh_token": os.getenv("SHOPEE_REFRESH_TOKEN_COMERCIAL")
        },
        "TOYS": {
            "partner_id": os.getenv("SHOPEE_PARTNER_ID_TOYS"),
            "partner_key": os.getenv("SHOPEE_PARTNER_KEY_TOYS"),
            "shop_id": os.getenv("SHOPEE_SHOP_ID_TOYS"),
            "refresh_token": os.getenv("SHOPEE_REFRESH_TOKEN_TOYS")
        }
    }
    for account, cfg in accounts.items():
        access_token, refresh_token = refresh_tokens(
            account, cfg["partner_id"], cfg["partner_key"], cfg["shop_id"], cfg["refresh_token"]
        )
        if access_token:
            print(f"✅ Tokens atualizados para {account}")
        else:
            print(f"❌ Falha ao atualizar tokens para {account}")

# USE ISSO NO INÍCIO DO FLUXO
atualizar_todos_tokens()

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
                if 'error' in resp_json:
                    error_code = resp_json.get('error', '')
                    if error_code in ['error_auth', 'error_token']:
                        if refresh_tokens(client):
                            continue
                        else:
                            retries += 1
                            continue
                if 'response' not in resp_json:
                    logging.warning("Resposta da API inválida")
                    return []
                order_list = resp_json['response'].get('order_list', [])
                if not order_list:
                    return []
                orders_sn = [o['order_sn'] for o in order_list]
                detalhes = client.order.get_order_detail(
                    order_sn_list=",".join(orders_sn),
                    response_optional_fields=",".join([
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
            order_data = {
                'order_sn': order.get('order_sn'),
                'create_time': order.get('create_time'),
                'order_status': order.get('order_status', '')
            }
            if not order_data['order_sn'] or not order_data['create_time']:
                continue
            if cursor.execute("SELECT 1 FROM pedidos WHERE order_sn = ?",
                              (order_data['order_sn'],)).fetchone():
                continue
            create_time_str = format_timestamp(order_data['create_time'])
            data_entregue = None
            if order_data['order_status'] == 'COMPLETED':
                create_date = datetime.strptime(create_time_str, "%Y-%m-%d %H:%M:%S")
                data_entregue = (create_date + timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
            valores = (
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
            logging.error(f"Erro no pedido {order_data.get('order_sn', '')}: {str(e)}")
    conn.commit()

def update_completed_orders(conn):
    cursor = conn.cursor()
    cursor.execute('''
        SELECT order_sn, create_time 
        FROM pedidos 
        WHERE order_status = 'COMPLETED' 
        AND Data_Entregue IS NULL
    ''')
    for order_sn, create_time in cursor.fetchall():
        try:
            create_date = datetime.strptime(create_time, "%Y-%m-%d %H:%M:%S")
            delivery_date = (create_date + timedelta(days=8)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute('''
                UPDATE pedidos 
                SET Data_Entregue = ? 
                WHERE order_sn = ?
            ''', (delivery_date, order_sn))
            logging.info(f"Pedido {order_sn} atualizado com Data_Entregue: {delivery_date}")
        except Exception as e:
            logging.error(f"Erro ao atualizar pedido {order_sn}: {str(e)}")
    conn.commit()

    import sqlite3
    import pandas as pd
    import json

    DB_PATH = r"C:\fisgarone\fisgarone.db"

def atualizar_preco_custo_em_vendas_shopee():
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE vendas_shopee
            SET PRECO_CUSTO = (
                SELECT Custo
                FROM custo_shopee
                WHERE custo_shopee.SKU = vendas_shopee.SKU
            )
            WHERE SKU IN (SELECT SKU FROM custo_shopee)
        """)
        conn.commit()
        conn.close()
        print("✅ Coluna PRECO_CUSTO atualizada na tabela 'vendas_shopee'.")

def processar_vendas_shopee():
    conn = sqlite3.connect(DB_PATH)
    pedidos = pd.read_sql_query("SELECT * FROM pedidos", conn)
    pedidos['DATA'] = pd.to_datetime(pedidos['create_time'], errors='coerce')
    pedidos['item_list'] = pedidos['item_list'].apply(json.loads)
    pedidos = pedidos.explode('item_list')
    itens_df = pd.json_normalize(pedidos['item_list'])
    itens_df.columns = [f'item_{col}' for col in itens_df.columns]
    pedidos = pedidos.drop(columns=['item_list']).reset_index(drop=True)
    pedidos = pd.concat([pedidos, itens_df], axis=1)

    def extrair_transportadora(pkg):
        try:
            pacotes = json.loads(pkg)
            if isinstance(pacotes, list) and len(pacotes) > 0:
                return pacotes[0].get('shipping_carrier', '')
        except:
            return ''
        return ''

    pedidos['TRANSPORTADORA'] = pedidos['package_list'].apply(extrair_transportadora)
    pedidos['TRANSPORTADORA'] = pedidos['TRANSPORTADORA'].replace({
        'SBS': 'Shopee Xpress',
        'SPX': 'Shopee Xpress',
        'STANDARD_EXPRESS': 'Shopee Xpress',
        'OTHER_LOGISTICS': 'Outros',
        'INHOUSE': 'Agência Shopee',
        'OWN_DELIVERY': 'Shopee Entrega Direta'
    })
    pedidos['PRECO_UNITARIO'] = pedidos['item_model_discounted_price'].astype(float)
    pedidos['QTD_COMPRADA'] = pedidos['item_model_quantity_purchased'].astype(int)
    pedidos['FRETE_TOTAL'] = pedidos['actual_shipping_fee'].astype(float)
    pedidos['VALOR_TOTAL'] = pedidos['PRECO_UNITARIO'] * pedidos['QTD_COMPRADA']
    pedidos['ITENS_PEDIDO'] = pedidos.groupby('order_sn')['order_sn'].transform('count')
    pedidos['FRETE_UNITARIO'] = pedidos['FRETE_TOTAL'] / pedidos['ITENS_PEDIDO']
    pedidos['DATA_ENTREGA'] = pd.NaT
    pedidos_completos = pedidos['order_status'] == 'COMPLETED'
    data_entregue_valida = pd.to_datetime(pedidos['Data_Entregue'], errors='coerce')
    pedidos.loc[pedidos_completos & data_entregue_valida.notna(), 'DATA_ENTREGA'] = data_entregue_valida
    pedidos['PRAZO_ENTREGA_DIAS'] = None
    pedidos.loc[pedidos['DATA_ENTREGA'].notna(), 'PRAZO_ENTREGA_DIAS'] = \
        (pedidos['DATA_ENTREGA'] - pedidos['DATA']).dt.total_seconds() / 86400
    pedidos['PRAZO_ENTREGA_DIAS'] = pedidos['PRAZO_ENTREGA_DIAS'].round(2)
    final = pedidos.rename(columns={
        'order_sn': 'PEDIDO_ID',
        'buyer_user_id': 'COMPRADOR_ID',
        'order_status': 'STATUS_PEDIDO',
        'account_type': 'TIPO_CONTA',
        'item_item_name': 'NOME_ITEM',
        'item_item_sku': 'SKU_ITEM',
        'item_model_sku': 'SKU_VARIACAO'
    })
    final['SKU'] = final.apply(
        lambda row: row['SKU_VARIACAO'] if pd.notna(row.get('SKU_VARIACAO')) and row['SKU_VARIACAO'] != '' else row.get('SKU_ITEM', ''),
        axis=1
    )

    # === Puxa o custo real pelo SKU ANTES dos cálculos ===
    conn_custo = sqlite3.connect(DB_PATH)
    df_custo = pd.read_sql_query("SELECT SKU, Custo FROM custo_shopee", conn_custo)
    conn_custo.close()
    final = final.merge(df_custo, how='left', left_on='SKU', right_on='SKU')
    final.rename(columns={'Custo': 'PRECO_CUSTO'}, inplace=True)
    final['PRECO_CUSTO'] = final['PRECO_CUSTO'].fillna(0)

    # === NOVO: custo total real (unitário * quantidade) ===
    final['CUSTO_TOTAL_REAL'] = (final['PRECO_CUSTO'] * final['QTD_COMPRADA']).round(2)

    final['COMISSAO_UNITARIA'] = (final['VALOR_TOTAL'] * 0.22).round(2)
    final['TAXA_FIXA'] = (final['QTD_COMPRADA'] * 4.00).round(2)
    final['TOTAL_COM_FRETE'] = final['VALOR_TOTAL']
    final['SM_CONTAS_PCT'] = final['TIPO_CONTA'].map({
        'TOYS': 9.27,
        'COMERCIAL': 7.06
    })
    final['SM_CONTAS_REAIS'] = (final['TOTAL_COM_FRETE'] * final['SM_CONTAS_PCT'] / 100).round(2)
    final['REPASSE_ENVIO'] = 0
    mask_envio = final['TRANSPORTADORA'] == 'Shopee Entrega Direta'
    first_index = final[mask_envio].groupby(['PEDIDO_ID', 'COMPRADOR_ID', 'DATA']).head(1).index
    final.loc[first_index, 'REPASSE_ENVIO'] = 8
    final['CUSTO_FIXO'] = (final['VALOR_TOTAL'] * 0.13).round(2)

    # === ATENÇÃO: agora usa CUSTO_TOTAL_REAL no cálculo! ===
    final['CUSTO_OP_TOTAL'] = (
        final[['CUSTO_TOTAL_REAL', 'COMISSAO_UNITARIA', 'TAXA_FIXA', 'SM_CONTAS_REAIS']]
        .apply(lambda x: pd.to_numeric(x, errors='coerce')).sum(axis=1)
    ).round(2)

    final['MARGEM_CONTRIBUICAO'] = (final['VALOR_TOTAL'] - final['CUSTO_OP_TOTAL']).round(2)
    final['LUCRO_REAL'] = (final['MARGEM_CONTRIBUICAO'] - final['CUSTO_FIXO']).round(2)
    final['LUCRO_REAL_PCT'] = (final['LUCRO_REAL'] / final['VALOR_TOTAL'] * 100).round(2)
    colunas_finais = [
        'PEDIDO_ID', 'COMPRADOR_ID', 'STATUS_PEDIDO', 'TIPO_CONTA', 'DATA',
        'NOME_ITEM', 'SKU', 'QTD_COMPRADA', 'PRECO_UNITARIO', 'PRECO_CUSTO',
        'CUSTO_TOTAL_REAL',  # Nova coluna adicionada
        'VALOR_TOTAL', 'FRETE_UNITARIO', 'COMISSAO_UNITARIA', 'TAXA_FIXA',
        'TOTAL_COM_FRETE', 'SM_CONTAS_PCT', 'SM_CONTAS_REAIS',
        'TRANSPORTADORA', 'DATA_ENTREGA', 'PRAZO_ENTREGA_DIAS', 'CUSTO_OP_TOTAL',
        'MARGEM_CONTRIBUICAO', 'CUSTO_FIXO', 'LUCRO_REAL', 'LUCRO_REAL_PCT', 'REPASSE_ENVIO'
    ]
    final = final[colunas_finais].drop_duplicates(subset=['PEDIDO_ID', 'SKU'], keep='first')
    final.to_sql("vendas_shopee", conn, if_exists="replace", index=False)
    conn.close()
    print("✅ Tabela 'vendas_shopee' atualizada com sucesso.")

def processar_repasses_shopee():
    conn = sqlite3.connect(DB_PATH)
    vendas = pd.read_sql_query("SELECT * FROM vendas_shopee", conn)
    colunas_repasses = ['PEDIDO_ID', 'DATA', 'VALOR_TOTAL', 'DATA_ENTREGA', 'COMISSAO_UNITARIA', 'TAXA_FIXA', 'STATUS_PEDIDO']
    repasses = vendas[colunas_repasses].drop_duplicates(subset=['PEDIDO_ID'])
    repasses.to_sql("repasses_shopee", conn, if_exists="replace", index=False)
    print(f"✅ Tabela 'repasses_shopee' atualizada com {len(repasses)} repasses.")

    # Aqui você cria o cursor e chama a função de atualização ANTES de fechar/commitar:
    cursor = conn.cursor()
    atualizar_entradas_financeiras(cursor)
    conn.commit()
    conn.close()


def main():
    print("\n=== AUTOMAÇÃO SHOPEE: INÍCIO ===")
    # 1. Verifica estrutura do banco
    conn = sqlite3.connect(DB_PATH)
    check_and_update_schema(conn)
    conn.close()
    print("[OK] Estrutura das tabelas garantida.")
    # 2. Baixa vendas
    print("[PASSO 1] Buscando pedidos/vendas da Shopee...")
    for conta in ["COMERCIAL", "TOYS"]:
        try:
            logging.info(f"Iniciando processamento para conta {conta}")
            client = create_shopee_client(conta)
            pedidos = fetch_orders(client, int((datetime.now(timezone.utc) - timedelta(days=60)).timestamp()))
            conn = sqlite3.connect(DB_PATH)
            insert_orders(pedidos, conn, conta)
            conn.close()
            logging.info(f"Conta {conta} processada com sucesso")
        except Exception as e:
            logging.error(f"Erro na conta {conta}: {str(e)}", exc_info=True)
    print("[OK] Tabela 'pedidos' atualizada.")
    # 3. Gera vendas_shopee (normaliza e agrega)
    print("[PASSO 2] Processando vendas_shopee (normalizando, agregando, custos etc)...")
    processar_vendas_shopee()
    # 4. Atualiza repasses_shopee
    print("[PASSO 3] Atualizando repasses_shopee...")
    processar_repasses_shopee()
    print("=== FINALIZADO ===")

if __name__ == "__main__":
    main()
