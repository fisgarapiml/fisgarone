import os
import sqlite3

# Caminho ABSOLUTO para a raiz do projeto
import os
DB_PATH = os.path.abspath("fisgarone.db")
print(f"DEBUG DB_PATH: {DB_PATH}")


# Conexão
conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

# Criação da tabela repasses_ml
cur.execute('''
CREATE TABLE IF NOT EXISTS repasses_ml (
    "ID Pedido" TEXT PRIMARY KEY,
    "Preco Unitario" REAL,
    "Data da Venda" TEXT,
    "Quantidade" INTEGER,
    "Tipo Logistica" TEXT,
    "Situacao" TEXT,
    "Taxa Fixa ML" REAL,
    "Comissoes" REAL,
    "Frete Seller" REAL
)
''')
conn.commit()

# MIGRAÇÃO dos dados da vendas_ml para repasses_ml
cur.execute('''
INSERT OR REPLACE INTO repasses_ml (
    "ID Pedido", "Preco Unitario", "Data da Venda", "Quantidade", "Tipo Logistica",
    "Situacao", "Taxa Fixa ML", "Comissoes", "Frete Seller"
)
SELECT 
    "ID Pedido",
    "Preco Unitario",
    "Data da Venda",
    "Quantidade",
    "Tipo Logistica",
    "Situacao",
    "Taxa Fixa ML",
    "Comissoes",
    COALESCE("Frete Seller", 0)  -- Ajuste: se não existir coluna, crie antes!
FROM vendas_ml
''')
conn.commit()

print("✅ Tabela repasses_ml criada e populada com sucesso.")

conn.close()
