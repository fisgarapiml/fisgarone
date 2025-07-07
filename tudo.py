import os
import sqlite3
import pandas as pd

DB_PATH = r"C:\fisgarone\fisgarone.db"
PLANILHA = r"C:\fisgarone\Custos Anúncios Shopee.xlsx"

def importar_custos():
    custos_df = pd.read_excel(PLANILHA)
    custos_df.columns = [col.strip().upper() for col in custos_df.columns]
    custos_df = custos_df.rename(columns={'SKU': 'SKU', 'CUSTO': 'Custo'})
    custos_df[['SKU', 'Custo']].to_sql('custo_shopee', sqlite3.connect(DB_PATH), if_exists='replace', index=False)
    print(f"✅ Tabela 'custo_shopee' criada/atualizada com {len(custos_df)} SKUs.")

if __name__ == "__main__":
    importar_custos()
