import os
import hmac
import hashlib
import requests
import time
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()


def generate_signature(partner_id, path, timestamp, partner_key):
    """Gera assinatura HMAC-SHA256 para autenticação."""
    base_string = f"{partner_id}{path}{timestamp}"
    signature = hmac.new(
        partner_key.encode(), base_string.encode(), hashlib.sha256
    ).hexdigest()
    return signature


def get_access_token_shop_level(shop_id, partner_id, partner_key, refresh_token):
    """Atualiza o token de acesso e refresh token usando a API da Shopee."""
    url = "https://partner.shopeemobile.com/api/v2/auth/access_token/get"
    timestamp = int(time.time())  # Correção para obter o timestamp correto
    path = "/api/v2/auth/access_token/get"
    sign = generate_signature(partner_id, path, timestamp, partner_key)

    headers = {"Content-Type": "application/json"}
    body = {
        "shop_id": int(shop_id),
        "refresh_token": refresh_token,
        "partner_id": int(partner_id)
    }

    params = {
        "partner_id": partner_id,
        "timestamp": timestamp,
        "sign": sign
    }

    response = requests.post(url, headers=headers, json=body, params=params)
    if response.status_code == 200:
        data = response.json()
        if "access_token" in data and "refresh_token" in data:
            return data["access_token"], data["refresh_token"]
        else:
            raise Exception(f"Erro ao obter tokens: {data}")
    else:
        raise Exception(f"Falha na requisição: {response.text}")


def update_env(access_token, refresh_token, prefix):
    """Atualiza o arquivo .env com os novos tokens."""
    # Verifica se o arquivo .env existe antes de ler
    if not os.path.exists('.env'):
        raise FileNotFoundError(".env não encontrado")

    # Abre o arquivo .env para leitura
    with open('.env', 'r') as file:
        lines = file.readlines()

    # Abre o arquivo .env para gravação
    with open('.env', 'w') as file:
        for line in lines:
            # Substitui a linha correspondente ao ACCESS_TOKEN
            if line.startswith(f"ACCESS_TOKEN_{prefix}="):
                file.write(f"ACCESS_TOKEN_{prefix}={access_token}\n")
            # Substitui a linha correspondente ao REFRESH_TOKEN
            elif line.startswith(f"REFRESH_TOKEN_{prefix}="):
                file.write(f"REFRESH_TOKEN_{prefix}={refresh_token}\n")
            else:
                file.write(line)


def main():
    # Defina as contas com prefixos e tokens necessários
    accounts = [
        {
            "prefix": "COMERCIAL",  # Prefixo ajustado para coincidir com as variáveis no .env
            "partner_id": os.getenv("PARTNER_ID_COMERCIAL"),
            "partner_key": os.getenv("PARTNER_KEY_COMERCIAL"),
            "shop_id": os.getenv("SHOP_ID_COMERCIAL"),
            "refresh_token": os.getenv("REFRESH_TOKEN_COMERCIAL"),
        },
        {
            "prefix": "TOYS",  # Prefixo ajustado para coincidir com as variáveis no .env
            "partner_id": os.getenv("PARTNER_ID_TOYS"),
            "partner_key": os.getenv("PARTNER_KEY_TOYS"),
            "shop_id": os.getenv("SHOP_ID_TOYS"),
            "refresh_token": os.getenv("REFRESH_TOKEN_TOYS"),
        },
    ]

    # Para cada conta, tente atualizar os tokens
    for account in accounts:
        print(f"Atualizando tokens para {account['prefix']}...")
        try:
            access_token, refresh_token = get_access_token_shop_level(
                account["shop_id"],
                account["partner_id"],
                account["partner_key"],
                account["refresh_token"],
            )
            update_env(access_token, refresh_token, account["prefix"])
            print(f"Tokens atualizados com sucesso para {account['prefix']}")
        except Exception as e:
            print(f"Erro ao atualizar tokens para {account['prefix']}: {e}")


if __name__ == "__main__":
    main()