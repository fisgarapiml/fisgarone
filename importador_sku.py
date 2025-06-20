import sqlite3
import pandas as pd
import os

# Configurações
DB_PATH = "grupo_fisgar.db"
PLANILHA_PATH = "Fornecedores_e_ SKus.xlsx"

COLUNA_DB = "codigo_fornecedor"
COLUNA_PLANILHA = "codigo_fornecedor"
COLUNA_SKU_PLANILHA = "SKU"
COLUNA_NOME_PLANILHA = "nome"

def adicionar_coluna_sku():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(produtos)")
        colunas = [col[1] for col in cursor.fetchall()]
        if 'SKU' not in colunas:
            cursor.execute("ALTER TABLE produtos ADD COLUMN SKU TEXT")
            print("✅ Coluna 'SKU' adicionada à tabela 'produtos'.")
        else:
            print("ℹ️ Coluna 'SKU' já existe na tabela 'produtos'.")

def carregar_planilha():
    df = pd.read_excel(PLANILHA_PATH, dtype=str)
    # Checa se colunas necessárias existem
    for coluna in [COLUNA_PLANILHA, COLUNA_SKU_PLANILHA, COLUNA_NOME_PLANILHA]:
        if coluna not in df.columns:
            raise Exception(f"Planilha não contém a coluna necessária: '{coluna}'")
    return df[[COLUNA_PLANILHA, COLUNA_SKU_PLANILHA, COLUNA_NOME_PLANILHA]].dropna()

def atualizar_sku_nome_produtos():
    df = carregar_planilha()
    # Monta mapeamento {codigo_fornecedor: (SKU, nome_otimizado)}
    mapeamento = {
        str(row[COLUNA_PLANILHA]): (str(row[COLUNA_SKU_PLANILHA]), str(row[COLUNA_NOME_PLANILHA]))
        for _, row in df.iterrows()
    }
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute(f"SELECT id, {COLUNA_DB}, nome FROM produtos")
        produtos = cursor.fetchall()
        count_atualizados = 0
        count_nao_encontrados = 0
        for prod in produtos:
            id_, cod_forn, nome_antigo = prod
            resultado = mapeamento.get(str(cod_forn))
            if resultado:
                sku, nome_novo = resultado
                cursor.execute("UPDATE produtos SET SKU = ?, nome = ? WHERE id = ?", (sku, nome_novo, id_))
                print(f"✔️ Atualizado ID {id_} | codigo_fornecedor={cod_forn} | SKU={sku} | nome='{nome_novo}'")
                count_atualizados += 1
            else:
                print(f"⚠️ Produto '{nome_antigo}' (codigo_fornecedor={cod_forn}) não encontrado na planilha.")
                count_nao_encontrados += 1
        conn.commit()
        print(f"\n✅ {count_atualizados} produtos atualizados com SKU e nome.")
        if count_nao_encontrados > 0:
            print(f"⚠️ {count_nao_encontrados} produtos não foram encontrados na planilha.")

# Pipeline principal
if __name__ == "__main__":
    if not os.path.exists(DB_PATH):
        print(f"❌ Banco de dados '{DB_PATH}' não encontrado.")
    elif not os.path.exists(PLANILHA_PATH):
        print(f"❌ Planilha '{PLANILHA_PATH}' não encontrada.")
    else:
        adicionar_coluna_sku()
        atualizar_sku_nome_produtos()
