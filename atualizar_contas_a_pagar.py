import os
import pandas as pd
import sqlite3
import re

# =====================
# CONFIGURAÇÕES INICIAIS
# =====================

# Caminho absoluto do banco local (muda aqui se for preciso)
DB_PATH = os.path.join(os.path.dirname(__file__), "grupo_fisgar.db")
TABELA = "contas_a_pagar"  # Alterado para a tabela correta
SHEET_ID = "1zj7fuvta2T55G0-cPnWthEfrVnqaui9u2EJ2cBJp64M"
SHEET_NAME = "contas a pagar"  # Alterado para a aba correta

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
    # Normalizar nomes das colunas
    df.columns = [normalizar_nome_coluna(c.lower().strip()) for c in df.columns]
    df.rename(columns=mapeamento_colunas, inplace=True)

    # Garantir que temos um código único
    if 'codigo' not in df.columns:
        df['codigo'] = range(1, len(df) + 1)

    # Preencher plano de contas se não existir
    if 'plano_de_contas' not in df.columns:
        df['plano_de_contas'] = "Outros"

    # Mapear categorias
    df['categorias'] = df['plano_de_contas'].map(mapeamento_categorias).fillna("Outros")

    # Mapear fornecedores e ajustar categorias
    for col in df.columns:
        if "nome___raz_o_social" in col:
            df['categorias'] = df[col].map(mapeamento_nome_razao_social).fillna(df['categorias'])
            df.rename(columns={col: "fornecedor"}, inplace=True)

    # Determinar tipo de custo
    df['tipo_custo'] = df['categorias'].apply(
        lambda x: "Fixo" if x == "Funcionários" or x == "Custo Fixo" else custo_fixo_variavel.get(x, "Variável")
    )

    # TRATAR VALORES MONETÁRIOS (garantir float, sem NaN, e valor_pago sempre float)
    for col in ['valor', 'valor_pendente', 'valor_pago']:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype(str)
                .str.replace(",", ".")
                .str.replace(r'[^\d\.-]', '', regex=True)
                .apply(lambda x: float(x) if x.strip() not in ['', '0', '0.0', '0.00', 'nan', 'None', None] else 0.0)
            )

    if 'valor' in df.columns:
        df['valor'] = df['valor'].apply(lambda x: -abs(x))  # Garante despesas negativas

    # VALOR_PAGO GARANTIDO COMO FLOAT >= 0
    if 'valor_pago' in df.columns:
        df['valor_pago'] = df['valor_pago'].apply(lambda x: float(x) if x is not None and x != '' else 0.0)

    # Remover duplicatas
    df.drop_duplicates(subset=['codigo'], inplace=True)
    print("✅ Dados processados com sucesso.")
    return df



def garantir_colunas_no_banco(df, banco, tabela):
    conn = sqlite3.connect(banco)
    cursor = conn.cursor()

    # Obter colunas existentes na tabela
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas_existentes = [info[1] for info in cursor.fetchall()]

    # Adicionar colunas que não existem
    for coluna in df.columns:
        if coluna not in colunas_existentes:
            try:
                cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} TEXT")
                print(f"✅ Coluna adicionada: {coluna}")
            except sqlite3.OperationalError as e:
                print(f"⚠️ Não foi possível adicionar a coluna {coluna}: {e}")

    conn.commit()
    conn.close()


def importar_para_sqlite(df, banco_dados, tabela):
    conn = sqlite3.connect(banco_dados)
    cursor = conn.cursor()

    # Preparar SQL para inserção/atualização
    colunas_insert = ", ".join([f'"{col}"' for col in df.columns])
    placeholders = ", ".join(["?" for _ in df.columns])
    update_set = ", ".join([f'"{col}"=excluded."{col}"' for col in df.columns if col != "codigo"])

    # Inserir/atualizar registros
    try:
        for _, row in df.iterrows():
            valores = tuple(row[col] for col in df.columns)
            cursor.execute(f'''
                INSERT INTO {tabela} ({colunas_insert}) VALUES ({placeholders})
                ON CONFLICT(codigo) DO UPDATE SET {update_set}
            ''', valores)

        conn.commit()
        print(f"✅ Dados importados com sucesso na tabela {tabela}.")
    except Exception as e:
        print(f"❌ Erro ao importar dados: {e}")
    finally:
        conn.close()


# =====================
# EXECUÇÃO PRINCIPAL
# =====================

def atualizar_compras_a_pagar():
    # Carregar dados da planilha
    df = carregar_planilha_google_sheets(SHEET_ID, SHEET_NAME)

    if df is not None:
        # Processar dados
        df_processado = processar_dados(df)

        if df_processado is not None:
            # Garantir que a tabela tem todas as colunas necessárias
            garantir_colunas_no_banco(df_processado, DB_PATH, TABELA)

            # Importar para o banco de dados
            importar_para_sqlite(df_processado, DB_PATH, TABELA)


if __name__ == "__main__":
    atualizar_compras_a_pagar()