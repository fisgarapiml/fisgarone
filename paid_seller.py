import sqlite3
import aiohttp
import asyncio
from dotenv import load_dotenv, set_key
import os
from datetime import datetime  # Import mantido conforme solicitado
from dateutil import parser  # Import mantido conforme solicitado

# Carrega .env
load_dotenv()

db_path = r"C:\fisgarone\grupo_fisgar.db"  # Caminho para seu banco de dados local
api_url = "https://api.mercadolibre.com"

# -- Dicionário multi-conta: seller_id como chave
# Certifique-se de que os SELLER_IDs no .env correspondem exatamente
# aos IDs usados na sua base de dados e na API.
# Ajustado para corresponder ao case do arquivo .env para seller_id_NOME
contas = [
    {
        "nome": "TOYS",
        "seller_id": str(os.getenv("seller_id_TOYS")),  # Alterado de SELLER_ID_TOYS
        "access_token": os.getenv("ACCESS_TOKEN_TOYS"),
        "refresh_token": os.getenv("REFRESH_TOKEN_TOYS"),
        "client_id": os.getenv("CLIENT_ID_TOYS"),
        "client_secret": os.getenv("CLIENT_SECRET_TOYS"),
    },
    {
        "nome": "COMERCIAL",
        "seller_id": str(os.getenv("seller_id_COMERCIAL")),  # Alterado de SELLER_ID_COMERCIAL
        "access_token": os.getenv("ACCESS_TOKEN_COMERCIAL"),
        "refresh_token": os.getenv("REFRESH_TOKEN_COMERCIAL"),
        "client_id": os.getenv("CLIENT_ID_COMERCIAL"),
        "client_secret": os.getenv("CLIENT_SECRET_COMERCIAL"),
    },
    {
        "nome": "PESCA",
        "seller_id": str(os.getenv("seller_id_PESCA")),  # Alterado de SELLER_ID_PESCA
        "access_token": os.getenv("ACCESS_TOKEN_PESCA"),
        "refresh_token": os.getenv("REFRESH_TOKEN_PESCA"),
        "client_id": os.getenv("CLIENT_ID_PESCA"),
        "client_secret": os.getenv("CLIENT_SECRET_PESCA"),
    },
    {
        "nome": "CAMPING",
        "seller_id": str(os.getenv("seller_id_CAMPING")),  # Alterado de SELLER_ID_CAMPING
        "access_token": os.getenv("ACCESS_TOKEN_CAMPING"),
        "refresh_token": os.getenv("REFRESH_TOKEN_CAMPING"),
        "client_id": os.getenv("CLIENT_ID_CAMPING"),
        "client_secret": os.getenv("CLIENT_SECRET_CAMPING"),
    }
]


def atualizar_env_token(account_name, new_access_token, new_refresh_token):
    """
    Atualiza os tokens no arquivo .env.
    """
    # Garante que account_name seja uppercase para consistência com as chaves do .env
    # Ex: ACCESS_TOKEN_TOYS (se account_name for "TOYS")
    env_account_key_name = account_name.upper()
    try:
        set_key('.env', f'ACCESS_TOKEN_{env_account_key_name}', new_access_token)
        set_key('.env', f'REFRESH_TOKEN_{env_account_key_name}', new_refresh_token)
        print(f"Tokens atualizados no .env para a conta: {account_name}")
    except Exception as e:
        print(f"Erro ao atualizar tokens no .env para {account_name}: {e}")


async def refresh_token(client_id, client_secret, refresh_token_value, session, account_name_for_log):
    """
    Atualiza o access token usando o refresh token.
    Retorna (new_access_token, new_refresh_token) ou (None, None) em caso de erro.
    """
    url = f"{api_url}/oauth/token"
    data = {
        'grant_type': 'refresh_token',
        'client_id': client_id,
        'client_secret': client_secret,
        'refresh_token': refresh_token_value  # Nome da variável alterado para clareza
    }
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}  # Boa prática adicionar

    print(f"Tentando atualizar token para a conta: {account_name_for_log} (Client ID: {client_id})")
    if not refresh_token_value:
        print(f"Erro: Refresh token está vazio ou nulo para a conta {account_name_for_log}.")
        return None, None

    async with session.post(url, data=data, headers=headers) as response:
        response_text = await response.text()  # Ler o texto da resposta para logs
        if response.status == 200:
            try:
                new_tokens = await response.json()  # Tentar converter para JSON apenas se status for 200
                print(f"Token atualizado com sucesso para a conta: {account_name_for_log}")
                return new_tokens.get('access_token'), new_tokens.get('refresh_token')
            except aiohttp.ContentTypeError:
                print(
                    f"Erro ao decodificar JSON da resposta de refresh token para {account_name_for_log}. Status: {response.status}. Resposta: {response_text}")
                return None, None
        else:
            print(
                f"Erro ao atualizar token para a conta {account_name_for_log} (Client ID: {client_id}). Status: {response.status} - Resposta: {response_text}")
            return None, None


async def fetch_repasses(access_token, order_id, session, account_name_for_log):
    """
    Busca detalhes de repasses para um order_id específico.
    """
    url = f"{api_url}/billing/integration/group/ML/order/details?order_ids={order_id}"
    headers = {"Authorization": f"Bearer {access_token}"}

    print(f"Buscando repasses para pedido {order_id} usando conta {account_name_for_log}")
    if not access_token:
        print(f"Erro: Access token está vazio ou nulo para a conta {account_name_for_log} ao buscar pedido {order_id}.")
        return None

    async with session.get(url, headers=headers) as response:
        response_text = await response.text()  # Ler o texto da resposta para logs
        if response.status == 200:
            try:
                return await response.json()  # Tentar converter para JSON apenas se status for 200
            except aiohttp.ContentTypeError:
                print(
                    f"Erro ao decodificar JSON da resposta de fetch_repasses para pedido {order_id}. Status: {response.status}. Resposta: {response_text}")
                return None
        elif response.status == 403:
            # 403 (Forbidden) - Provavelmente problema de permissão/escopo do token
            print(
                f"Erro 403 (Proibido) para pedido {order_id} na conta {account_name_for_log}. Verifique as permissões/escopos do aplicativo no Mercado Livre. Resposta da API: {response_text}")
        elif response.status == 401:
            # 401 (Unauthorized) - Provavelmente token inválido ou expirado que não foi atualizado corretamente
            print(
                f"Erro 401 (Não Autorizado) para pedido {order_id} na conta {account_name_for_log}. Token pode estar inválido. Resposta da API: {response_text}")
        else:
            print(
                f"Erro ao buscar repasses para pedido {order_id} na conta {account_name_for_log}. Status: {response.status} - Resposta da API: {response_text}")
        return None


async def importar_repasses():
    """
    Importa os repasses do Mercado Livre e atualiza a tabela seller_pagamentos.
    """
    # --- Pega todos os pedidos únicos e seller_ids da vendas_ml ---
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            # Garanta que os nomes das colunas "ID Pedido" e "Conta" estão corretos
            # e que a coluna "Conta" armazena o seller_id correspondente.
            cursor.execute(
                'SELECT DISTINCT "ID Pedido", "Conta" FROM vendas_ml WHERE "ID Pedido" IS NOT NULL AND "Conta" IS NOT NULL')
            pedidos = cursor.fetchall()  # Lista de tuplas: (id_pedido, seller_id_da_venda)
    except sqlite3.Error as e:
        print(f"Erro ao conectar ou consultar o banco de dados (vendas_ml): {e}")
        return

    if not pedidos:
        print("Nenhum pedido encontrado na tabela vendas_ml para processar.")
        return

    print(f"Total de {len(pedidos)} pedidos únicos encontrados para processar.")

    async with aiohttp.ClientSession() as session:
        with sqlite3.connect(db_path) as conn_insert:  # Conexão separada para inserts
            cursor_insert = conn_insert.cursor()
            for id_pedido, seller_id_da_venda in pedidos:
                if not seller_id_da_venda:
                    print(f"Pedido {id_pedido} não possui seller_id associado na tabela vendas_ml. Pulando.")
                    continue

                # Encontra a configuração da conta baseada no seller_id_da_venda
                conta_config = next((c for c in contas if c["seller_id"] == str(seller_id_da_venda).strip()), None)

                if not conta_config:
                    print(
                        f"Configuração de conta NÃO encontrada para seller_id '{seller_id_da_venda}' (associado ao pedido {id_pedido}). Verifique o .env e a coluna 'Conta' em vendas_ml. Pulando pedido.")
                    continue

                if not conta_config.get("client_id") or not conta_config.get("client_secret") or not conta_config.get(
                        "refresh_token"):
                    print(
                        f"Credenciais incompletas (client_id, client_secret, ou refresh_token) para a conta {conta_config['nome']} (Seller ID: {seller_id_da_venda}). Pulando pedido {id_pedido}.")
                    continue

                print(
                    f"\nProcessando pedido {id_pedido} para conta {conta_config['nome']} (Seller ID: {seller_id_da_venda})")

                # Tenta refrescar o token antes de consumir a API de repasses
                # É crucial que o refresh_token no .env seja válido.
                new_access_token, new_refresh_token_val = await refresh_token(
                    conta_config["client_id"],
                    conta_config["client_secret"],
                    conta_config["refresh_token"],  # Passa o valor atual do refresh token
                    session,
                    conta_config["nome"]
                )

                if new_access_token and new_refresh_token_val:
                    # Atualiza os tokens na configuração em memória e no .env
                    conta_config["access_token"] = new_access_token
                    conta_config[
                        "refresh_token"] = new_refresh_token_val  # Atualiza com o novo refresh token, se retornado
                    atualizar_env_token(conta_config["nome"], new_access_token, new_refresh_token_val)
                elif not conta_config["access_token"]:  # Se o refresh falhou e não havia um access token anterior
                    print(
                        f"Falha ao obter access token para a conta {conta_config['nome']} e não há token antigo. Pulando pedido {id_pedido}.")
                    continue
                # Se o refresh falhar mas já existir um access_token na config, tenta usá-lo.
                # A API pode retornar 401 se estiver expirado, o que será logado.

                # Chama a API de repasses
                json_data = await fetch_repasses(conta_config["access_token"], id_pedido, session, conta_config["nome"])

                if not json_data or not json_data.get("results"):
                    print(
                        f"Não foram encontrados 'results' nos dados do repasse para o pedido {id_pedido} da conta {conta_config['nome']}. Pulando.")
                    continue

                # Processa os resultados
                # A API retorna uma lista em "results", mesmo para um único order_id
                for order_detail_result in json_data.get("results", []):
                    payment_infos = order_detail_result.get("payment_info", [])
                    details_list = order_detail_result.get("details",
                                                           [])  # Renomeado para evitar conflito com módulo 'details'

                    for payment in payment_infos:
                        retencao_impostos = 0.0
                        retencao_iva = 0.0
                        debitos_creditos = 0.0
                        sirtac = 0.0

                        tax_details = payment.get("tax_details", [])
                        for tax in tax_details:
                            ent = tax.get("mov_financial_entity", "")
                            # Garante que o valor seja numérico e trata None ou string vazia
                            try:
                                val_str = tax.get("original_amount", "0")
                                val = float(val_str if val_str is not None else 0)
                            except ValueError:
                                val = 0.0
                                print(
                                    f"Alerta: 'original_amount' inválido ('{tax.get('original_amount')}') em tax_details para pedido {id_pedido}. Usando 0.")

                            if ent == "retencion_ganancias":
                                retencao_impostos += val
                            elif ent == "retencion_iva":
                                retencao_iva += val
                            elif ent == "debitos_creditos":  # Corrigido de "debitos_creditos_financ"
                                debitos_creditos += val
                            elif ent == "cordoba":  # Supondo que "cordoba" é um tipo de sirtac ou retenção específica
                                sirtac += val
                            # Adicione mais 'elif' se houver outras entidades financeiras de imposto

                        data_aprovacao = payment.get("date_approved")
                        data_criacao = payment.get("date_created")
                        data_liberacao = payment.get("money_release_date")
                        dias_liberacao = payment.get("money_release_days")
                        status_liberacao = payment.get("money_release_status")
                        status_pagamento = payment.get("status")  # Renomeado para evitar conflito
                        detalhes_status = payment.get("status_details")
                        id_pagamento = payment.get("payment_id")
                        id_comprador = payment.get("payer_id")
                        metodo_pagamento = payment.get("payment_method_id")
                        tipo_pagamento = payment.get("payment_type_id")

                        try:
                            valor_transacao_str = payment.get("transaction_amount", "0")
                            valor_transacao = float(valor_transacao_str if valor_transacao_str is not None else 0)
                        except ValueError:
                            valor_transacao = 0.0
                            print(
                                f"Alerta: 'transaction_amount' inválido ('{payment.get('transaction_amount')}') para pedido {id_pedido}. Usando 0.")

                        try:
                            total_financiamento_str = payment.get("financing_transfer_total", "0")
                            total_financiamento = float(
                                total_financiamento_str if total_financiamento_str is not None else 0)
                        except ValueError:
                            total_financiamento = 0.0

                        try:
                            taxa_financiamento_str = payment.get("financing_fee", "0")
                            taxa_financiamento = float(
                                taxa_financiamento_str if taxa_financiamento_str is not None else 0)
                        except ValueError:
                            taxa_financiamento = 0.0

                        # 'details_list' contém informações sobre itens, envio, etc.
                        for det_item_level in details_list:  # Renomeado para clareza
                            sales_infos_list = det_item_level.get("sales_info", [{}])  # Pode ser uma lista
                            sales_info_data = sales_infos_list[
                                0] if sales_infos_list else {}  # Pega o primeiro, se existir

                            shipping_info = det_item_level.get("shipping_info", {})
                            items_infos_list = det_item_level.get("items_info", [{}])  # Pode ser uma lista
                            discount_info = det_item_level.get("discount_info", {})
                            charge_info = det_item_level.get("charge_info", {})

                            for item in items_infos_list:  # Itera sobre os itens
                                try:
                                    # Prepara os dados para inserção no banco
                                    dados_pagamento = (
                                        conta_config["nome"],
                                        str(id_pedido),  # ID do Pedido (Order ID)
                                        str(id_pagamento),  # ID do Pagamento
                                        data_aprovacao,
                                        data_criacao,
                                        data_liberacao,
                                        dias_liberacao,
                                        status_liberacao,
                                        id_comprador,
                                        metodo_pagamento,
                                        tipo_pagamento,
                                        status_pagamento,
                                        detalhes_status,
                                        valor_transacao,
                                        total_financiamento,
                                        taxa_financiamento,
                                        item.get("item_id"),
                                        item.get("item_title"),
                                        item.get("item_type"),
                                        item.get("item_category"),
                                        item.get("item_amount"),  # Quantidade do item
                                        item.get("item_price"),  # Preço unitário do item
                                        det_item_level.get("marketplace_info", {}).get("marketplace"),
                                        det_item_level.get("currency_info", {}).get("currency_id"),
                                        sales_info_data.get("sale_date_time"),
                                        sales_info_data.get("sales_channel"),
                                        sales_info_data.get("payer_nickname"),
                                        sales_info_data.get("state_name"),
                                        retencao_impostos,
                                        retencao_iva,
                                        debitos_creditos,
                                        sirtac,
                                        charge_info.get("detail_amount"),
                                        charge_info.get("detail_type"),
                                        charge_info.get("detail_sub_type"),
                                        shipping_info.get("receiver_shipping_cost"),
                                        discount_info.get("discount_amount"),
                                        discount_info.get("discount_reason")
                                    )

                                    # SQL de inserção (garanta que a ordem e número de '?' correspondem)
                                    sql_insert = """
                                    INSERT OR IGNORE INTO seller_pagamentos (
                                        tipo_conta, id_pedido, id_pagamento, data_aprovacao, data_criacao, data_liberacao,
                                        dias_liberacao, status_liberacao, id_comprador, metodo_pagamento, tipo_pagamento, status, detalhes_status,
                                        valor_transacao, total_financiamento, taxa_financiamento, id_item, titulo_item, tipo_item, categoria_item,
                                        quantidade_item, preco_item, marketplace, moeda, data_venda, canal_venda, apelido_comprador, estado,
                                        retencao_impostos, retencao_iva, debitos_creditos, sirtac, valor_cobranca, tipo_cobranca, subtipo_cobranca,
                                        custo_envio, valor_desconto, motivo_desconto
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    """
                                    cursor_insert.execute(sql_insert, dados_pagamento)
                                except sqlite3.Error as e_sql:
                                    print(
                                        f"Erro ao inserir pagamento do pedido {id_pedido}, item {item.get('item_id')} no banco: {e_sql}. Dados: {dados_pagamento}")
                                except Exception as e_geral:
                                    print(
                                        f"Erro geral ao processar item {item.get('item_id')} do pedido {id_pedido}: {e_geral}")

                conn_insert.commit()  # Commit após processar todos os pagamentos e itens de um pedido
                print(f"Dados do pedido {id_pedido} processados e salvos/ignorados no banco.")

    print("\nImportação de repasses do Mercado Livre (pagamentos) concluída.")
    print("Verifique os logs para erros 403 ou outros problemas.")
    print(
        "Se os erros 403 persistirem, revise as permissões (escopos) do seu aplicativo no painel de desenvolvedores do Mercado Livre.")


if __name__ == "__main__":
    # Para rodar o asyncio corretamente no Windows em alguns cenários
    # asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy()) # Descomente se necessário no Windows

    # Verifica se o .env existe e se as variáveis essenciais estão carregadas
    # Reestruturado para maior clareza e para evitar potenciais erros de parsing

    missing_seller_ids = not all(os.getenv(f"seller_id_{acc['nome']}") for acc in contas)
    missing_client_ids = not all(os.getenv(f"CLIENT_ID_{acc['nome']}") for acc in contas)
    missing_client_secrets = not all(os.getenv(f"CLIENT_SECRET_{acc['nome']}") for acc in contas)
    missing_refresh_tokens = not all(os.getenv(f"REFRESH_TOKEN_{acc['nome']}") for acc in contas)

    if missing_seller_ids or missing_client_ids or missing_client_secrets or missing_refresh_tokens:
        print("ALERTA: Uma ou mais variáveis de ambiente (.env) para as contas não foram carregadas.")
        print("Verifique seu arquivo .env e os nomes das variáveis (ex: seller_id_TOYS, ACCESS_TOKEN_TOYS, etc.)")
        # Decida se quer parar a execução ou continuar com as contas que estão configuradas
        # exit() # descomente para parar se as variáveis forem críticas

    asyncio.run(importar_repasses())
