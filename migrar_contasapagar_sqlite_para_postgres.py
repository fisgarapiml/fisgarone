import sqlite3
from sqlalchemy import create_engine, inspect, Table, MetaData
import os
from dotenv import load_dotenv
import unicodedata

# Carrega variáveis do .env
load_dotenv()

SQLITE_DB = 'grupo_fisgar.db'
TABELA = 'contas_a_pagar'
POSTGRES_URL = os.getenv('DATABASE_URL')

def sanitize_value(val):
    if val is None:
        return None
    try:
        # Converte para string se necessário, decodifica bytes
        if isinstance(val, bytes):
            return val.decode('utf-8', 'replace')
        # Se for string, só retorna
        return str(val)
    except Exception:
        try:
            # Remove caracteres especiais, acentuação etc
            return unicodedata.normalize('NFKD', str(val)).encode('ascii', 'ignore').decode('ascii')
        except Exception:
            return None

# 1. Ler do SQLite
sqlite_conn = sqlite3.connect(SQLITE_DB)
sqlite_cursor = sqlite_conn.cursor()
sqlite_cursor.execute(f"SELECT * FROM {TABELA}")
rows = sqlite_cursor.fetchall()
colunas = [desc[0] for desc in sqlite_cursor.description]
sqlite_conn.close()

# 2. Preparar conexão com PostgreSQL
pg_engine = create_engine(POSTGRES_URL)
metadata = MetaData()
inspector = inspect(pg_engine)
if not inspector.has_table(TABELA):
    print(f"A tabela '{TABELA}' não existe no Postgres. Rode o app para criá-la antes.")
    exit(1)
tabela_pg = Table(TABELA, metadata, autoload_with=pg_engine)

novos = 0
batch_size = 50  # Menor lote para garantir não travar a Render Free
registros_com_erro = []

for i in range(0, len(rows), batch_size):
    batch = rows[i:i+batch_size]
    with pg_engine.begin() as conn:
        for row in batch:
            row_dict = dict(zip(colunas, row))
            # Sanitiza todos os campos para evitar erro de encoding
            for k, v in row_dict.items():
                row_dict[k] = sanitize_value(v)

            codigo = row_dict.get('codigo')
            fornecedor = row_dict.get('fornecedor')
            nome_razao = row_dict.get('nome___raz_o_social')
            if (fornecedor is None or str(fornecedor).strip() == '') and nome_razao not in (None, '', ' '):
                row_dict['fornecedor'] = nome_razao

            existe = conn.execute(
                tabela_pg.select().where(tabela_pg.c.codigo == codigo)
            ).fetchone()
            if not existe:
                campos_pg = [c.name for c in tabela_pg.columns]
                registro_final = {k: v for k, v in row_dict.items() if k in campos_pg}
                try:
                    conn.execute(tabela_pg.insert().values(**registro_final))
                    novos += 1
                except Exception as e:
                    print(f"Erro ao inserir codigo={codigo}: {e}")
                    registros_com_erro.append(codigo)
    print(f"Lote {i//batch_size+1} finalizado ({min(i+batch_size, len(rows))}/{len(rows)}) registros processados.")

print(f"\nProcesso finalizado: {novos} lançamentos migrados para o Postgres!")
if registros_com_erro:
    print("Atenção! Os seguintes códigos não foram migrados devido a erro e precisam ser revisados manualmente:")
    print(registros_com_erro)
