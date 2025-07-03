import sqlite3

ORIGEM = 'grupo_fisgar.db'
DESTINO = 'fisgarone.db'
TABELA = 'vendas_ml'

def migrar_tabela_completa(origem_db, destino_db, nome_tabela):
    # Conectar ao banco de origem e destino
    con_origem = sqlite3.connect(origem_db)
    con_destino = sqlite3.connect(destino_db)
    cur_origem = con_origem.cursor()
    cur_destino = con_destino.cursor()

    # Buscar o SQL original da tabela (estrutura exata)
    cur_origem.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{nome_tabela}'")
    ddl = cur_origem.fetchone()
    if ddl is None:
        raise Exception(f"Tabela {nome_tabela} não existe no banco de origem!")

    # Cria igual no destino, apagando antes se existir
    cur_destino.execute(f"DROP TABLE IF EXISTS {nome_tabela}")
    cur_destino.execute(ddl[0])
    con_destino.commit()

    # Copia todos os dados
    cur_origem.execute(f"SELECT * FROM {nome_tabela}")
    linhas = cur_origem.fetchall()
    if linhas:
        # Busca nome das colunas na ordem
        cur_origem.execute(f"PRAGMA table_info({nome_tabela})")
        colunas = [row[1] for row in cur_origem.fetchall()]
        placeholders = ",".join(["?"] * len(colunas))
        cur_destino.executemany(
            f"INSERT INTO {nome_tabela} VALUES ({placeholders})", linhas
        )
        con_destino.commit()
        print(f"✅ {len(linhas)} registros migrados para {nome_tabela}")
    else:
        print(f"⚠️ Tabela {nome_tabela} está vazia, sem dados migrados.")

    con_origem.close()
    con_destino.close()

if __name__ == "__main__":
    migrar_tabela_completa(ORIGEM, DESTINO, TABELA)
