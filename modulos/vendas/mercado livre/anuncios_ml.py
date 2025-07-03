import os
import requests
import time
import sqlite3
from dotenv import load_dotenv, set_key
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DB_PATH = os.path.join(BASE_DIR, "grupo_fisgar.db")
TABELA = "anuncios_ml"
ENV_FILE = os.path.join(BASE_DIR, ".env")

load_dotenv(ENV_FILE)
# ===== 1. Tabela (Criação automática) =====
def criar_tabela_anuncios_ml():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            CREATE TABLE IF NOT EXISTS {TABELA} (
                mlb TEXT PRIMARY KEY,
                titulo TEXT,
                sku TEXT,
                preco REAL,
                estoque INTEGER,
                status TEXT,
                conta TEXT,
                categoria TEXT,
                url TEXT,
                data_criacao TEXT,
                data_update TEXT,
                imagens TEXT
            )
        """)
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABELA}_conta ON {TABELA} (conta)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABELA}_status ON {TABELA} (status)")
        cursor.execute(f"CREATE INDEX IF NOT EXISTS idx_{TABELA}_sku ON {TABELA} (sku)")
        conn.commit()
        print(f"✅ Tabela {TABELA} pronta!")

def upsert_anuncio(anuncio: dict):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {TABELA} (
                mlb, titulo, sku, preco, estoque, status, conta, categoria, url, data_criacao, data_update, imagens
            ) VALUES (
                :mlb, :titulo, :sku, :preco, :estoque, :status, :conta, :categoria, :url, :data_criacao, :data_update, :imagens
            )
            ON CONFLICT(mlb) DO UPDATE SET
                titulo=excluded.titulo,
                sku=excluded.sku,
                preco=excluded.preco,
                estoque=excluded.estoque,
                status=excluded.status,
                conta=excluded.conta,
                categoria=excluded.categoria,
                url=excluded.url,
                data_criacao=excluded.data_criacao,
                data_update=excluded.data_update,
                imagens=excluded.imagens
        """, anuncio)
        conn.commit()

# ===== 2. Integração mercado_livre =====
load_dotenv()

ACCOUNTS = [
    {
        "name": "PESCA",
        "client_id": os.getenv("CLIENT_ID_PESCA"),
        "client_secret": os.getenv("CLIENT_SECRET_PESCA"),
    },
    {
        "name": "TOYS",
        "client_id": os.getenv("CLIENT_ID_TOYS"),
        "client_secret": os.getenv("CLIENT_SECRET_TOYS"),
    },
    {
        "name": "CAMPING",
        "client_id": os.getenv("CLIENT_ID_CAMPING"),
        "client_secret": os.getenv("CLIENT_SECRET_CAMPING"),
    },
    {
        "name": "COMERCIAL",
        "client_id": os.getenv("CLIENT_ID_COMERCIAL"),
        "client_secret": os.getenv("CLIENT_SECRET_COMERCIAL"),
    },
]

ML_API_URL = "https://api.mercadolibre.com"

def get_tokens(account_name: str) -> (str, str):
    access = os.getenv(f"ACCESS_TOKEN_{account_name}")
    refresh = os.getenv(f"REFRESH_TOKEN_{account_name}")
    return access, refresh

def save_tokens(account_name: str, access: str, refresh: str):
    set_key(ENV_FILE, f"ACCESS_TOKEN_{account_name}", access)
    set_key(ENV_FILE, f"REFRESH_TOKEN_{account_name}", refresh)

def refresh_access_token(account: dict) -> Optional[str]:
    refresh_token = os.getenv(f"REFRESH_TOKEN_{account['name']}")
    data = {
        "grant_type": "refresh_token",
        "client_id": account["client_id"],
        "client_secret": account["client_secret"],
        "refresh_token": refresh_token,
    }
    response = requests.post(f"{ML_API_URL}/oauth/token", data=data, timeout=10)
    if response.status_code == 200:
        resp = response.json()
        save_tokens(account["name"], resp["access_token"], resp["refresh_token"])
        print(f"✅ Token atualizado para {account['name']}")
        return resp["access_token"]
    else:
        print(f"❌ Falha ao atualizar token para {account['name']}: {response.text}")
        return None

def request_with_auto_refresh(account: dict, url: str, method="GET", **kwargs):
    access_token, _ = get_tokens(account["name"])
    headers = kwargs.pop("headers", {})
    headers["Authorization"] = f"Bearer {access_token}"
    try:
        r = requests.request(method, url, headers=headers, timeout=10, **kwargs)
    except requests.RequestException as ex:
        print(f"Erro de conexão: {ex}")
        return None
    if r is not None and r.status_code == 401:
        # Token inválido ou expirado. Tentar refresh e retry!
        new_access_token = refresh_access_token(account)
        if not new_access_token:
            print(f"Token não pôde ser renovado para {account['name']}. Pulando conta.")
            return None
        headers["Authorization"] = f"Bearer {new_access_token}"
        try:
            r = requests.request(method, url, headers=headers, timeout=10, **kwargs)
        except requests.RequestException as ex:
            print(f"Erro de conexão após refresh: {ex}")
            return None
    if r is not None and not r.ok:
        print(f"Erro API ML: {r.status_code} {r.text}")
    return r

def get_user_id(account: dict) -> Optional[int]:
    r = request_with_auto_refresh(account, f"{ML_API_URL}/users/me")
    if r and r.ok:
        return r.json().get("id")
    return None

def fetch_all_listing_ids(account: dict) -> List[str]:
    user_id = get_user_id(account)
    if not user_id:
        print(f"User_id não obtido para conta {account['name']}. Pulando...")
        return []
    offset = 0
    limit = 50
    max_offset = 950  # API limita para 1000
    listing_ids = []
    while True:
        if offset > max_offset:
            print(f"Atingido limite de paginação para conta {account['name']} (max_offset={max_offset}). Use filtros para paginar por status.")
            break
        url = f"{ML_API_URL}/users/{user_id}/items/search?offset={offset}&limit={limit}&access_token={os.getenv(f'ACCESS_TOKEN_{account['name']}')}"
        r = request_with_auto_refresh(account, url)
        if r and r.ok:
            result = r.json()
            ids = result.get("results", [])
            listing_ids.extend(ids)
            if len(ids) < limit:
                break
            offset += limit
        else:
            print(f"Falha ao buscar anúncios: {r.text if r else ''}")
            break
    return listing_ids

def fetch_listing_detail(account: dict, item_id: str, retry=2) -> Dict[str, Any]:
    url = f"{ML_API_URL}/items/{item_id}?access_token={os.getenv(f'ACCESS_TOKEN_{account['name']}')}"
    for attempt in range(retry):
        try:
            r = request_with_auto_refresh(account, url)
            if r and r.ok:
                return r.json()
        except Exception as e:
            print(f"Erro ({e}) ao detalhar anúncio {item_id}, tentativa {attempt+1}")
            time.sleep(1)
    return {}

def sync_ads(account: dict) -> List[Dict[str, Any]]:
    print(f"Sincronizando anúncios da conta {account['name']}")
    all_ads = []
    ids = fetch_all_listing_ids(account)
    print(f"Total de anúncios encontrados: {len(ids)}")
    for i, item_id in enumerate(ids):
        detail = fetch_listing_detail(account, item_id)
        if not detail.get("id"):
            print(f"Erro ao detalhar anúncio {item_id}, pulando.")
            continue
        ad = {
            "mlb": detail.get("id"),
            "titulo": detail.get("title"),
            "sku": detail.get("seller_custom_field"),
            "preco": detail.get("price"),
            "estoque": detail.get("available_quantity"),
            "status": detail.get("status"),
            "conta": account["name"],
            "categoria": detail.get("category_id"),
            "url": detail.get("permalink"),
            "data_criacao": detail.get("date_created"),
            "data_update": detail.get("last_updated"),
            "imagens": ",".join([p.get("secure_url") for p in detail.get("pictures", []) if p.get("secure_url")]),
        }
        upsert_anuncio(ad)
        all_ads.append(ad)
        if (i+1) % 20 == 0:
            print(f"{i+1}/{len(ids)} anúncios processados")
        time.sleep(0.1)
    return all_ads

def sync_all_accounts():
    all_ads = []
    for acc in ACCOUNTS:
        try:
            ads = sync_ads(acc)
            print(f"Conta {acc['name']} => {len(ads)} anúncios sincronizados")
            all_ads.extend(ads)
        except Exception as e:
            print(f"Erro ao sincronizar {acc['name']}: {e}")
    return all_ads

if __name__ == "__main__":
    criar_tabela_anuncios_ml()
    anuncios = sync_all_accounts()
    print(f"Total geral de anúncios: {len(anuncios)}")
