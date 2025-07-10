import sqlite3

DB_PATH = r"C:\fisgarone\fisgarone.db"
with sqlite3.connect(DB_PATH) as conn:
    cursor = conn.cursor()
    # Adiciona coluna se não existir
    cursor.execute("PRAGMA table_info(repasses_shopee)")
    colunas = [c[1] for c in cursor.fetchall()]
    if 'TIPO_CONTA' not in colunas:
        cursor.execute('ALTER TABLE repasses_shopee ADD COLUMN TIPO_CONTA TEXT')
        print("Coluna TIPO_CONTA adicionada em repasses_shopee!")
    else:
        print("Coluna TIPO_CONTA já existe em repasses_shopee.")
    conn.commit()
