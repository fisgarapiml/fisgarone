import sqlite3

CAMINHO_BANCO = "grupo_fisgar.db"  # Altere se seu .db tiver outro nome

def adicionar_coluna_editado_local():
    conn = sqlite3.connect(CAMINHO_BANCO)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(contas_a_pagar)")
    colunas = [info[1] for info in cursor.fetchall()]
    if 'editado_local' not in colunas:
        cursor.execute("ALTER TABLE contas_a_pagar ADD COLUMN editado_local TEXT DEFAULT '0'")
        print("✅ Coluna 'editado_local' adicionada com sucesso!")
    else:
        print("Coluna 'editado_local' já existe.")
    conn.commit()
    conn.close()

if __name__ == "__main__":
    adicionar_coluna_editado_local()
