import sqlite3

DB = 'grupo_fisgar.db'

def atualizar_tabela_produtos_processados():
    conn = sqlite3.connect(DB)
    cursor = conn.cursor()

    # Verifica se a coluna já existe
    cursor.execute("PRAGMA table_info(produtos_processados)")
    colunas = [col[1] for col in cursor.fetchall()]

    if 'qtd_por_volume_extraida' not in colunas:
        cursor.execute("ALTER TABLE produtos_processados ADD COLUMN qtd_por_volume_extraida INTEGER")
        print("✅ Coluna 'qtd_por_volume_extraida' adicionada com sucesso.")
    else:
        print("ℹ️ A coluna 'qtd_por_volume_extraida' já existe.")

    conn.commit()
    conn.close()

if __name__ == '__main__':
    atualizar_tabela_produtos_processados()
