import sqlite3
from sqlalchemy import create_engine, MetaData, Table
import os
from dotenv import load_dotenv

load_dotenv()

SQLITE_DB = 'grupo_fisgar.db'
TABELA = 'contas_a_pagar'
POSTGRES_URL = os.getenv('DATABASE_URL')

# 1. Pega só um registro do SQLite
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute(f"SELECT * FROM {TABELA} LIMIT 1")
row = sqlite_cursor.fetchone()
colunas = [desc[0] for desc in sqlite_cursor.description]
sqlite_conn.close()

if row is None:
    print("Nenhum registro encontrado no SQLite.")
    exit(1)

print("\nRegistro lido do SQLite:")
print(dict(zip(colunas, row)))

# 2. Tenta inserir esse registro na nuvem
engine = create_engine(POSTGRES_URL)
metadata = MetaData()
tabela_pg = Table(TABELA, metadata, autoload_with=engine)
codigo = dict(zip(colunas, row)).get('codigo')

with engine.begin() as conn:
    # Checa se já existe
    existe = conn.execute(tabela_pg.select().where(tabela_pg.c.codigo == codigo)).fetchone()
    if existe:
        print("Esse registro já existe na nuvem (Postgres).")
    else:
        registro = dict(zip(colunas, row))
        if (not registro['fornecedor'] or str(registro['fornecedor']).strip() == '') and registro['nome___raz_o_social']:
            registro['fornecedor'] = registro['nome___raz_o_social']
        campos_pg = [c.name for c in tabela_pg.columns]
        registro_final = {k: v for k, v in registro.items() if k in campos_pg}
        print("\nTentando inserir o registro na nuvem:")
        print(registro_final)
        try:
            conn.execute(tabela_pg.insert().values(**registro_final))
            print("Registro inserido com sucesso!")
        except Exception as e:
            print("Erro ao inserir:", e)
