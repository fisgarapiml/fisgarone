import sqlite3
import os

# Caminho absoluto do banco
DB_PATH = os.path.join(os.path.dirname(__file__), 'grupo_fisgar.db')

# Conexão
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# TABELA 1 - PRODUTOS
cursor.execute("DROP TABLE IF EXISTS produtos")
cursor.execute('''
CREATE TABLE produtos (
     codigo_fornecedor INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    unidade_compra TEXT,
    quantidade INTEGER,
    valor_total REAL,
    ipi REAL,
    fator_conversao INTEGER,
    custo_unitario REAL,
    custo_com_ipi REAL,
    atualizado_em TEXT,
    categorias TEXT,
    status TEXT,
    qtd_volumes INTEGER,
    qtd_por_volume INTEGER,
    qtd_real_unidades INTEGER,
    custo_volume REAL,
    data_atualizacao TEXT,
    numero_nfe TEXT,
    data_emissao TEXT,
    caminho_xml TEXT,
    fornecedor TEXT,
    origem TEXT
)
''')

# TABELA 2 - CONTAS_A_PAGAR
cursor.execute("DROP TABLE IF EXISTS contas_a_pagar")
cursor.execute('''
CREATE TABLE contas_a_pagar (
    codigo INTEGER PRIMARY KEY AUTOINCREMENT,
    vencimento TEXT,
    fornecedor TEXT,
    banco_pagamento TEXT,
    valor REAL,
    valor_pago REAL,
    valor_pendente REAL,
    documento TEXT,
    documento_tipo TEXT,
    pagamento_tipo TEXT,
    plano_de_contas TEXT,
    data_cadastro TEXT,
    comentario TEXT,
    empresa TEXT,
    conta TEXT,
    status TEXT,
    categorias TEXT,
    tipo_custo TEXT,
    centro_de_custo TEXT,
    tipo TEXT,
    data_pagamento TEXT,
    arquivo_pagamento TEXT,
    arquivo_documento TEXT,
    arquivo_xml TEXT,
    arquivo_boleto TEXT
)
''')

# TABELA 3 - NFE_PROCESSADAS
cursor.execute("DROP TABLE IF EXISTS nfe_processadas")
cursor.execute('''
CREATE TABLE nfe_processadas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    numero_nfe TEXT NOT NULL UNIQUE,
    chave_acesso TEXT,
    fornecedor TEXT,
    data_emissao TEXT,
    total_nota REAL,
    caminho_xml TEXT,
    data_importacao TEXT
)
''')

conn.commit()
conn.close()
print("✅ Tabelas recriadas com sucesso.")
