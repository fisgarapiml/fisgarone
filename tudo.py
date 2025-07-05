import sqlite3

DB_PATH = "C:/fisgarone/fisgarone.db"

with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()

    # Adicionar coluna (se ainda não existe)
    try:
        cursor.execute('ALTER TABLE repasses_ml ADD COLUMN "Total da Venda" REAL')
    except sqlite3.OperationalError:
        pass  # Já existe

    try:
        cursor.execute('ALTER TABLE repasses_ml ADD COLUMN "Total Custo" REAL')
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute('ALTER TABLE repasses_ml ADD COLUMN "Valor do Repasse" REAL')
    except sqlite3.OperationalError:
        pass

    # Atualizar as colunas com os cálculos
    cursor.execute("""
        UPDATE repasses_ml
        SET
            "Total da Venda" = "Preco Unitario" * "Quantidade",
            "Total Custo" = COALESCE("Taxa Fixa ML",0) + COALESCE("Comissoes",0) + COALESCE("Frete Seller",0),
            "Valor do Repasse" = ("Preco Unitario" * "Quantidade") - (COALESCE("Taxa Fixa ML",0) + COALESCE("Comissoes",0) + COALESCE("Frete Seller",0))
    """)
    conn.commit()
print('Atualizado!')
