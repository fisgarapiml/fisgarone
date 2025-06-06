import os
import pandas as pd
import sqlite3
import re

# =====================
# CONFIGURAÇÕES INICIAIS
# =====================

# Caminho absoluto do banco local (muda aqui se for preciso)
DB_PATH = os.path.join(os.path.dirname(__file__), "grupo_fisgar.db")
TABELA = "contas_a_pagar"
SHEET_ID = "1zj7fuvta2T55G0-cPnWthEfrVnqaui9u2EJ2cBJp64M"
SHEET_NAME = "compras"

# =====================
# MAPEAMENTOS
# =====================

mapeamento_categorias = {
    "Café da Manhã": "Alimentação",
    "Reembolsos": "Custo de vendas",
    "Procuradoria PGFN": "Impostos",
    "Inmetro 40x25": "Insumos",
    "DAS de Parcelamento": "Dívidas Parceladas",
    "Padrão": "Simples Nacional",
    "Sistema Integrador": "Software",
    "Point Ships (Pipoca)": "Fornecedores",
    "Kikakau (Bolibol)": "Fornecedores",
    "Billispel": "Fornecedores",
    "Aluguel": "Fixo",
    "Fatura": "Cartões",
    "Jhan": "Fornecedores",
    "vale transporte": "Funcionários",
    "salário": "Funcionários",
    "bonificação": "Funcionários",
    "fgts": "Funcionários",
    "Gabriel": "Funcionários",
    "Lara Peçanha": "Funcionários",
    "Jtoys": "Fornecedores",
    "Miniplay": "Fornecedores",
    "Marsil Atacadista": "Fornecedores",
    "Manos Doces": "Fornecedores",
    "Point Chips": "Fornecedores",
    "Nucita": "Fornecedores",
    "ALFA FULGA COMERCIIO": "Fornecedores",
    "Contabilidade": "Custo Fixo",
    "Altamiris Goes": "Custo Fixo"
}

mapeamento_nome_razao_social = {
    "Edilson": "Funcionários",
    "Anderson": "Funcionários",
    "Simone": "Funcionários",
    "Suelen Produção": "Funcionários",
    "Sávio": "Funcionários",
    "Lara Peçanha": "Funcionários",
    "Gabriel Arthur": "Funcionários",
    "Altamiris Goes": "Funcionários",
    "J TOYS BRINQUEDO LEGAL LTDA": "Fornecedores",
    "Rio de Ondas Restaurante": "Fornecedores",
    "Mercado Haquiza - Café": "Fornecedores",
    "Mini Play Industria de Comercio de Plasticos LTDA": "Fornecedores",
    "LIVRARIA FONTES DE CONHECIMENTO LTDA": "Fornecedores",
    "ALFA FULGA COMERCIO (Oliveira Embalagens)": "Fornecedores",
    "Mano's Doces": "Fornecedores",
    "WA Transportes - Flex Shopee": "Fornecedores",
    "Embalagem para Envios (Caixas)": "Fornecedores",
    "R. L. PINHEIRO & CIA LTDA - Pipoca": "Fornecedores",
    "Restaurante": "Fornecedores",
    "EBAZAR.COM.BR LTDA (Mercado Livre)": "Fornecedores",
    "ENVOS Lalamove": "Fornecedores",
    "FGTS": "Impostos",
    "Simples Nacional": "Impostos",
    "Simples Nacional Fisgar Brinquedos": "Impostos",
    "Simples Nacional Fisgar Pesca": "Impostos",
    "Simples Nacional Comercial Mota": "Impostos",
    "Imposto Prefeitura": "Impostos",
    "LF CONSULTORIA SOLUÇÕES E DESENVOLVIMENTO - IdWorks": "Software",
    "Conta Vivo Plano Mensal (Internet/Telefone)": "Água/Luz/Telefone",
    "Energia": "Água/Luz/Telefone",
    "Água": "Água/Luz/Telefone",
    "VALENT'S DESCARTAVEIS LTDA": "Fornecedores",
    "Simples Nacional Fisgar Camping": "Impostos",
    "Reembolso": "Custo de vendas",
    "Prolabores": "Funcionários",
    "Parcelamento de Simples": "Impostos",
    "MAGALU/ACORDO": "Dívidas Parceladas",
    "LIMPA NOME": "Outros",
    "LF CONSULTORIA SOLUCOES E DESENVOLVIMENTO - IdWorks": "Software",
    "Junior": "Funcionários",
    "IGOR": "Funcionários",
    "Gabriel": "Funcionários",
    "Frete de Fornecedor": "Fornecedores",
    "Fornecedores": "Fornecedores",
    "Envios Lalamove": "Fornecedores",
    "Empresa": "Outros",
    "Elismar Mota": "Funcionários",
    "EDS -Mercado Livre /Mercado Pago": "Fornecedores",
    "EBAZAR.COM.BR LTDA": "Fornecedores",
    "Conta Vivo Plano Mensal": "Água/Luz/Telefone",
    "Bianca Balieiro Silva": "Funcionários",
    "Banco Santander": "Outros",
    "Banco Caixa": "Outros",
    "BANCO BRADESCO S.A.": "Outros",
    "Asonet": "Fornecedores",
    "Alarme": "Outros"
}

custo_fixo_variavel = {
    "salário": "Fixo",
    "advocacia": "Fixo",
    "vale transporte": "Fixo",
    "água": "Fixo",
    "energia": "Fixo",
    "telefone": "Fixo",
    "vale refeição": "Fixo",
    "fgts": "Fixo",
    "acordo/empréstimo": "Fixo",
    "contabilidade": "Fixo",
    "das de parcelamento": "Fixo",
    "aluguel": "Fixo",
    "impostos": "Variável",
    "insumos": "Variável",
    "custo de vendas": "Variável",
    "software": "Fixo",
    "fornecedores": "Variável",
    "cartões": "Variável",
    "Altamiris Goes": "Fixo",
    "Funcionários": "Fixo",
    "Dívidas Parceladas": "Fixo",
    "Água/Luz/Telefone": "Fixo",
    "Outros": "Variável"
}

mapeamento_colunas = {
    "r__valor": "valor",
    "r__pendente": "valor_pendente",
    "r__pago": "valor_pago",
    "coment_rios": "comentario",
    "c_digo": "codigo_externo",
    "n__documento": "documento",
    "data_compet_ncia": "data_competencia"
}

# =====================
# FUNÇÕES AUXILIARES
# =====================

def normalizar_nome_coluna(nome):
    return re.sub(r'[^a-zA-Z0-9_]', '_', nome)

def carregar_planilha_google_sheets(sheet_id, aba):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba}"
    try:
        df = pd.read_csv(url)
        print("✅ Planilha carregada com sucesso do Google Sheets.")
        return df
    except Exception as e:
        print(f"❌ Erro ao carregar a planilha: {e}")
        return None

def processar_dados(df):
    df.columns = [normalizar_nome_coluna(c.lower().strip()) for c in df.columns]
    df.rename(columns=mapeamento_colunas, inplace=True)

    if 'codigo' not in df.columns:
        df['codigo'] = range(1, len(df) + 1)

    if 'plano_de_contas' not in df.columns:
        df['plano_de_contas'] = "Outros"

    df['categorias'] = df['plano_de_contas'].map(mapeamento_categorias).fillna("Outros")

    for col in df.columns:
        if "nome___raz_o_social" in col:
            df['categorias'] = df[col].map(mapeamento_nome_razao_social).fillna(df['categorias'])
            df.rename(columns={col: "fornecedor"}, inplace=True)

    df['tipo_custo'] = df['categorias'].apply(
        lambda x: "Fixo" if x == "Funcionários" or x == "Custo Fixo" else custo_fixo_variavel.get(x, "Variável")
    )

    for col in ['valor', 'valor_pendente', 'valor_pago']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", ".").str.strip()

    if 'valor' in df.columns:
        df['valor'] = df['valor'].astype(float)
        df['valor'] = df['valor'].apply(lambda x: -abs(x))

    df.drop_duplicates(subset=['codigo'], inplace=True)
    print("✅ Dados processados com sucesso.")
    return df

def garantir_colunas_no_banco(df, banco, tabela):
    conn = sqlite3.connect(banco)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas_existentes = [info[1] for info in cursor.fetchall()]
    for coluna in df.columns:
        if coluna not in colunas_existentes:
            cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} TEXT")
            print(f"✅ Coluna adicionada: {coluna}")
    conn.commit()
    conn.close()

def importar_para_sqlite(df, banco_dados, tabela):
    conn = sqlite3.connect(banco_dados)
    cursor = conn.cursor()
    colunas_insert = ", ".join([f'"{col}"' for col in df.columns])
    placeholders = ", ".join(["?" for _ in df.columns])
    update_set = ", ".join([f'{col}=excluded.{col}' for col in df.columns if col != "codigo"])

    for _, row in df.iterrows():
        valores = tuple(row[col] for col in df.columns)
        cursor.execute(f'''
            INSERT INTO {tabela} ({colunas_insert}) VALUES ({placeholders})
            ON CONFLICT(codigo) DO UPDATE SET {update_set}
        ''', valores)

    conn.commit()
    conn.close()
    print("✅ Dados importados com sucesso no banco SQLite.")

# =====================
# EXECUÇÃO PRINCIPAL
# =====================

def atualizar_contas_a_pagar():
    print("🔄 Atualizando tabela contas_a_pagar do .db local com Google Sheets...")
    df = carregar_planilha_google_sheets(SHEET_ID, SHEET_NAME)
    if df is not None:
        df_processado = processar_dados(df)
        if df_processado is not None:
            garantir_colunas_no_banco(df_processado, DB_PATH, TABELA)
            importar_para_sqlite(df_processado, DB_PATH, TABELA)
            print("✅ Atualização automática concluída!")
        else:
            print("❌ Falha ao processar os dados.")
    else:
        print("❌ Falha ao carregar a planilha.")

if __name__ == "__main__":
    atualizar_contas_a_pagar()
