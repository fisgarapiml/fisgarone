import sqlite3

db_path = r"C:\fisgarone\grupo_fisgar.db"
with sqlite3.connect(db_path) as conn:
    cursor = conn.cursor()

    # Atualiza Taxa Fixa ML
    cursor.execute("""
        UPDATE vendas_ml
        SET "Taxa Fixa ML" =
            CASE
                WHEN "Preco Unitario" < 79 AND "MLB" IN ('MLB3776836339', 'MLB3804566539', 'MLB5116841236')
                    THEN 1 * COALESCE("Quantidade",0)
                WHEN "Preco Unitario" < 79
                    THEN 6 * COALESCE("Quantidade",0)
                ELSE 0
            END;
    """)

    # Atualiza Comissoes
    cursor.execute("""
        UPDATE vendas_ml
        SET "Comissoes" = (COALESCE("Taxa Mercado Livre",0) * COALESCE("Quantidade",0)) - COALESCE("Taxa Fixa ML",0);
    """)

    # Atualiza Comissao (%)
    cursor.execute("""
        UPDATE vendas_ml
        SET "Comissao (%)" =
            CASE 
                WHEN COALESCE("Preco Unitario",0) * COALESCE("Quantidade",0) = 0 THEN 0
                ELSE COALESCE("Comissoes",0) / (COALESCE("Preco Unitario",0) * COALESCE("Quantidade",0))
            END;
    """)

    conn.commit()
print("Tudo recalculado conforme a nova lógica!")
