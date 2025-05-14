import sqlite3
conn = sqlite3.connect("grupo_fisgar.db")
cursor = conn.cursor()
cursor.execute("PRAGMA table_info(contas_a_pagar)")
for coluna in cursor.fetchall():
    print(coluna)
conn.close()
