import sqlite3
import pandas as pd

DB_PATH = r"C:\fisgarone\fisgarone.db"

def auditoria_vendas_shopee():
    print("⏳ Rodando auditoria da Shopee...")
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM vendas_shopee", conn)
    conn.close()

    # Cálculos esperados:
    df["mc_total_esperado"] = (df["VALOR_TOTAL"] - df["CUSTO_OP_TOTAL"]).round(2)
    df["custo_fixo_esperado"] = (df["VALOR_TOTAL"] * 0.13).round(2)
    df["lucro_real_esperado"] = (df["mc_total_esperado"] - df["custo_fixo_esperado"]).round(2)
    df["lucro_real_pct_esperado"] = (df["lucro_real_esperado"] / df["VALOR_TOTAL"] * 100).round(2)

    # Diferenças
    df["dif_mc_total"] = (df["MARGEM_CONTRIBUICAO"].round(2) - df["mc_total_esperado"])
    df["dif_custo_fixo"] = (df["CUSTO_FIXO"].round(2) - df["custo_fixo_esperado"])
    df["dif_lucro_real"] = (df["LUCRO_REAL"].round(2) - df["lucro_real_esperado"])
    df["dif_lucro_real_pct"] = (df["LUCRO_REAL_PCT"].round(2) - df["lucro_real_pct_esperado"])

    # SÓ exibe linhas com diferença relevante (maior que 0.01 ou menor que -0.01)
    erros = df[
        (df["dif_mc_total"].abs() > 0.01) |
        (df["dif_custo_fixo"].abs() > 0.01) |
        (df["dif_lucro_real"].abs() > 0.01) |
        (df["dif_lucro_real_pct"].abs() > 0.01)
    ].copy()

    # Só para visual, mostra as principais colunas e as diferenças
    if not erros.empty:
        print("🚨 ERROS ENCONTRADOS (SHOPEE):")
        print(erros[[
            "PEDIDO_ID", "VALOR_TOTAL", "MARGEM_CONTRIBUICAO", "mc_total_esperado", "dif_mc_total",
            "CUSTO_FIXO", "custo_fixo_esperado", "dif_custo_fixo",
            "LUCRO_REAL", "lucro_real_esperado", "dif_lucro_real",
            "LUCRO_REAL_PCT", "lucro_real_pct_esperado", "dif_lucro_real_pct"
        ]].head(30))  # Mostra só as 30 primeiras linhas problemáticas para facilitar debug
        print(f"\nTOTAL DE LINHAS COM ERRO: {len(erros)}")
    else:
        print("✅ Nenhum erro encontrado. Cálculos Shopee estão perfeitos!")

    # Se quiser salvar para Excel:
    # erros.to_excel("erros_vendas_shopee.xlsx", index=False)

# Para rodar isolado:
if __name__ == "__main__":
    auditoria_vendas_shopee()
