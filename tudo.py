import sqlite3
import os

# Caminhos dos bancos na raiz
NOVO_DB = os.path.join(os.path.dirname(__file__), 'fisgarone.db')
ANTIGO_DB = os.path.join(os.path.dirname(__file__), 'grupo_fisgar.db')  # Troque pelo nome correto!

def migrar_contas_a_pagar():
    conn_novo = sqlite3.connect(NOVO_DB)
    conn_antigo = sqlite3.connect(ANTIGO_DB)
    cur_novo = conn_novo.cursor()
    cur_antigo = conn_antigo.cursor()

    # Busca todos os dados da tabela antiga
    cur_antigo.execute("SELECT * FROM contas_a_pagar")
    registros = cur_antigo.fetchall()

    # Prepara a inserção no novo banco
    if registros:
        print(f'Migrando {len(registros)} registros...')
        placeholders = ','.join('?' * len(registros[0]))
        sql = f"INSERT INTO contas_a_pagar VALUES ({placeholders})"
        cur_novo.executemany(sql, registros)
        conn_novo.commit()
        print('Migração concluída!')
    else:
        print('Nada para migrar.')

    conn_antigo.close()
    conn_novo.close()

if __name__ == '__main__':
    migrar_contas_a_pagar()
