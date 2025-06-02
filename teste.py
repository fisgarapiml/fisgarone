import sqlite3

conn = sqlite3.connect('grupo_fisgar.db')
cur = conn.cursor()

# TRATAMENTO DE "Tipo Logistica"
cur.execute("""
    UPDATE vendas_ml SET "Tipo Logistica" = 'Full' WHERE "Tipo Logistica" = 'fulfillment'
""")
cur.execute("""
    UPDATE vendas_ml SET "Tipo Logistica" = 'Flex' WHERE "Tipo Logistica" = 'self_service'
""")
cur.execute("""
    UPDATE vendas_ml SET "Tipo Logistica" = 'Ponto de Coleta' WHERE "Tipo Logistica" = 'xd_drop_off'
""")

# TRATAMENTO DE "Conta"
cur.execute("""
    UPDATE vendas_ml SET "Conta" = 'Toys ML' WHERE "Conta" = '555536943'
""")
cur.execute("""
    UPDATE vendas_ml SET "Conta" = 'Comercial ML' WHERE "Conta" = '202989490'
""")
cur.execute("""
    UPDATE vendas_ml SET "Conta" = 'Pesca ML' WHERE "Conta" = '263678949'
""")
cur.execute("""
    UPDATE vendas_ml SET "Conta" = 'Camping ML' WHERE "Conta" = '702704896'
""")

conn.commit()
conn.close()

print("Substituição de Tipo Logistica e Conta feita com sucesso!")
