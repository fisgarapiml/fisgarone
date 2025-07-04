import sqlite3
import pandas as pd
import os

import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
DB_PATH = os.path.join(BASE_DIR, 'fisgarone.db')
PLANILHA_CUSTOS = os.path.join(BASE_DIR, 'Custos Anúncios mercado livre.xlsx')

print(f"[DEBUG] Banco: {DB_PATH}")
print(f"[DEBUG] Planilha: {PLANILHA_CUSTOS}")

if not os.path.exists(DB_PATH):
    print(f"❌ Banco de dados '{DB_PATH}' não encontrado.")
else:
    print(f"✅ Banco de dados encontrado!")

if not os.path.exists(PLANILHA_CUSTOS):
    print(f"❌ Planilha '{PLANILHA_CUSTOS}' não encontrada.")
else:
    print(f"✅ Planilha encontrada!")


COLUNA_MLB = 'CÓD. VARIAÇÃO CANAL'
COLUNA_CUSTO = 'CUSTO'
COLUNA_DESTINO = 'Preço Custo ML'
COLUNA_ALIQUOTA = 'Aliquota (%)'
COLUNA_IMPOSTO_REAIS = 'Imposto R$'
COLUNA_FRETE_COMPRADOR = 'Frete Comprador'
COLUNA_FRETE_SELLER = 'Frete Seller'
COLUNA_CUSTO_OP = 'Custo Operacional'
COLUNA_COMISSAO = 'Comissoes'
COLUNA_TAXA_FIXA = 'Taxa Fixa ML'
COLUNA_TOTAL_CUSTO_OP = 'Total Custo Operacional'
COLUNA_MC_TOTAL = 'MC Total'
COLUNA_CUSTO_FIXO = 'Custo Fixo'
COLUNA_LUCRO_REAL = 'Lucro Real'
COLUNA_LUCRO_REAL_PCT = 'Lucro Real %'

ALIQUOTAS = {
    'COMERCIAL': 7.06,
    'PESCA': 5.54,
    'SHOP': 9.27,
    'CAMPING': 4.00
}

def verificar_colunas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(vendas_ml)")
    colunas = [col[1] for col in cursor.fetchall()]

    for coluna in [
        COLUNA_DESTINO, COLUNA_ALIQUOTA, COLUNA_IMPOSTO_REAIS,
        COLUNA_FRETE_COMPRADOR, COLUNA_FRETE_SELLER,
        COLUNA_CUSTO_OP, COLUNA_COMISSAO, COLUNA_TAXA_FIXA,
        COLUNA_TOTAL_CUSTO_OP, COLUNA_MC_TOTAL, COLUNA_CUSTO_FIXO,
        COLUNA_LUCRO_REAL, COLUNA_LUCRO_REAL_PCT
    ]:
        if coluna not in colunas:
            cursor.execute(f'ALTER TABLE vendas_ml ADD COLUMN "{coluna}" REAL')
            print(f"✅ Coluna '{coluna}' adicionada.")

    conn.commit()
    conn.close()

def carregar_planilha():
    df_raw = pd.read_excel(PLANILHA_CUSTOS, header=None)
    linha_cabecalho = df_raw.apply(lambda row: row.astype(str).str.contains(COLUNA_MLB, case=False).any(), axis=1)
    idx = linha_cabecalho.idxmax()
    df = pd.read_excel(PLANILHA_CUSTOS, header=idx)
    return df[[COLUNA_MLB, COLUNA_CUSTO]].dropna()

def atualizar_preco_custo_ml(df):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    atualizados = 0

    for _, row in df.iterrows():
        mlb = str(row[COLUNA_MLB]).strip()
        custo_unitario = row[COLUNA_CUSTO]
        if mlb and pd.notna(custo_unitario):
            cursor.execute(f'''
                UPDATE vendas_ml
                SET "{COLUNA_DESTINO}" = (Quantidade * ?)
                WHERE MLB = ?
            ''', (float(custo_unitario), mlb))
            atualizados += cursor.rowcount

    conn.commit()
    conn.close()
    print(f"✅ Preço Custo ML atualizado em {atualizados} registros.")

def aplicar_aliquotas():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    atualizados = 0

    for conta, aliquota in ALIQUOTAS.items():
        cursor.execute(f'''
            UPDATE vendas_ml
            SET "{COLUNA_ALIQUOTA}" = ?
            WHERE UPPER(Conta) = ?
        ''', (aliquota, conta.upper()))
        atualizados += cursor.rowcount

    conn.commit()
    conn.close()
    print(f"✅ Alíquotas aplicadas em {atualizados} registros.")

def calcular_imposto_reais():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f'''
        UPDATE vendas_ml
        SET "{COLUNA_IMPOSTO_REAIS}" = ROUND(("Preco Unitario" * Quantidade * "{COLUNA_ALIQUOTA}") / 100, 2)
        WHERE "{COLUNA_ALIQUOTA}" IS NOT NULL AND Quantidade IS NOT NULL AND "Preco Unitario" IS NOT NULL
    ''')

    conn.commit()
    conn.close()
    print(f"✅ Coluna '{COLUNA_IMPOSTO_REAIS}' calculada com sucesso.")

def calcular_fretes():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql("SELECT rowid, * FROM vendas_ml", conn)

    custo_total_col = [col for col in df.columns if col.lower().strip() == 'custo total frete']
    custo_lista_col = [col for col in df.columns if col.lower().strip() == 'custo lista frete']
    if not custo_total_col or not custo_lista_col:
        raise ValueError("Colunas 'Custo Total Frete' ou 'Custo Lista Frete' não encontradas na tabela.")

    frete_total = custo_total_col[0]
    frete_lista = custo_lista_col[0]

    media_frete_seller = df.loc[
        (df['Pago Por'].str.lower() == 'seller') &
        (df[frete_total] == 0) &
        (df[frete_lista] == 0)
    ][frete_lista].mean()

    def determinar_fretes(row):
        preco = row['Preco Unitario']
        frete_custo_total = row[frete_total]
        frete_custo_lista = row[frete_lista]
        pago_por = str(row.get("Pago Por", '')).lower()

        if pago_por == 'seller' and frete_custo_total == 0 and frete_custo_lista == 0:
            return pd.Series([0, media_frete_seller])
        elif preco >= 79:
            return pd.Series([0, frete_custo_lista])
        elif preco < 79:
            return pd.Series([frete_custo_total, 0])
        else:
            return pd.Series([0, 0])

    df[[COLUNA_FRETE_COMPRADOR, COLUNA_FRETE_SELLER]] = df.apply(determinar_fretes, axis=1)

    for _, row in df.iterrows():
        conn.execute(f'''
            UPDATE vendas_ml SET
                "{COLUNA_FRETE_COMPRADOR}" = ?,
                "{COLUNA_FRETE_SELLER}" = ?
            WHERE rowid = ?
        ''', (row[COLUNA_FRETE_COMPRADOR], row[COLUNA_FRETE_SELLER], row['rowid']))

    conn.commit()
    conn.close()
    print("✅ Cálculo de fretes comprador/seller aplicado com sucesso.")

def calcular_custo_operacional():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f'''
        UPDATE vendas_ml
        SET "{COLUNA_CUSTO_OP}" = ROUND("Preco Unitario" * Quantidade * 0.04, 2)
        WHERE "Preco Unitario" IS NOT NULL AND Quantidade IS NOT NULL
    ''')

    cursor.execute(f'''
        UPDATE vendas_ml
        SET "{COLUNA_TOTAL_CUSTO_OP}" = 
            COALESCE("{COLUNA_DESTINO}",0) + 
            COALESCE("{COLUNA_IMPOSTO_REAIS}",0) + 
            COALESCE("{COLUNA_CUSTO_OP}",0) + 
            COALESCE("{COLUNA_COMISSAO}",0) + 
            COALESCE("{COLUNA_TAXA_FIXA}",0) + 
            COALESCE("{COLUNA_FRETE_SELLER}",0)
    ''')

    conn.commit()
    conn.close()
    print("✅ Total de custo operacional atualizado com todos os componentes.")

def calcular_margem_lucro():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute(f'''
        UPDATE vendas_ml
        SET "{COLUNA_MC_TOTAL}" = ROUND(("Preco Unitario" * Quantidade) - COALESCE("{COLUNA_TOTAL_CUSTO_OP}",0), 2),
            "{COLUNA_CUSTO_FIXO}" = ROUND(("Preco Unitario" * Quantidade) * 0.13, 2),
            "{COLUNA_LUCRO_REAL}" = ROUND(("{COLUNA_MC_TOTAL}" - "{COLUNA_CUSTO_FIXO}"), 2),
            "{COLUNA_LUCRO_REAL_PCT}" = CASE 
                WHEN ("Preco Unitario" * Quantidade) > 0 THEN ROUND(("{COLUNA_LUCRO_REAL}" / ("Preco Unitario" * Quantidade)) * 100, 2)
                ELSE NULL
            END
        WHERE "Preco Unitario" IS NOT NULL AND Quantidade IS NOT NULL
    ''')

    conn.commit()
    conn.close()
    print("✅ MC total, custo fixo, lucro real e % recalculados.")

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Banco de dados '{DB_PATH}' não encontrado.")
        return

    if not os.path.exists(PLANILHA_CUSTOS):
        print(f"❌ Planilha '{PLANILHA_CUSTOS}' não encontrada.")
        return

    verificar_colunas()
    df = carregar_planilha()
    atualizar_preco_custo_ml(df)
    aplicar_aliquotas()
    calcular_imposto_reais()
    calcular_fretes()
    calcular_custo_operacional()
    calcular_margem_lucro()

if __name__ == '__main__':
    main()
