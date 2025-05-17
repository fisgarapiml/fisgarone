import sqlite3
import unicodedata

# 1) Ajuste para o caminho do seu SQLite
DB_PATH = r'C:\fisgarone\grupo_fisgar.db'

# 2) Os dicionários de mapeamento conforme você enviou
mapeamento_categorias = {
    "Café da Manhã": "Alimentação",
    "Reembolsos": "Custo de Vendas",
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
    "Altamiris Goes": "Custo Fixo",
    "Simples Nacional": "Impostos"
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
    # ... (restante do seu mapeamento)
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

def normalize(text):
    """Remove acentos, põe em minúsculas e trim."""
    if not text:
        return ''
    text = text.strip().lower()
    # remove acentos
    return ''.join(c for c in unicodedata.normalize('NFD', text)
                   if unicodedata.category(c) != 'Mn')

# pré-normaliza as chaves dos mapas
map_cat = {normalize(k): v for k,v in mapeamento_categorias.items()}
map_nome = {normalize(k): v for k,v in mapeamento_nome_razao_social.items()}
map_cfv = {normalize(k): v for k,v in custo_fixo_variavel.items()}

def atualizar_categorias_e_tipo(db_path):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Lê todos os registros
    registros = cur.execute("""
        SELECT codigo, plano_de_contas, nome___raz_o_social
        FROM contas_a_pagar
    """).fetchall()

    for row in registros:
        codigo = row['codigo']
        plano_raw = row['plano_de_contas']
        nome_raw = row['nome___raz_o_social']

        plano = normalize(plano_raw)
        nome  = normalize(nome_raw)

        # 1) Descobre nova categoria pelo plano
        categoria = map_cat.get(plano)
        # 2) Se não achou, tenta pelo nome/razão social
        if not categoria and nome:
            categoria = map_nome.get(nome)

        # 3) Determina tipo_custo por categoria (ou, se quiser, por plano)
        tipo = None
        if categoria:
            tipo = map_cfv.get(normalize(categoria))
        else:
            tipo = map_cfv.get(plano)

        # 4) Prepara lista de updates
        updates = []
        params = []
        if categoria:
            updates.append("categorias = ?")
            params.append(categoria)
        if tipo:
            updates.append("tipo_custo = ?")
            params.append(tipo)

        # 5) Executa se ao menos um campo mudou
        if updates:
            sql = f"UPDATE contas_a_pagar SET {', '.join(updates)} WHERE codigo = ?"
            params.append(codigo)
            cur.execute(sql, params)

    conn.commit()
    conn.close()
    print("Atualização concluída com sucesso.")

if __name__ == "__main__":
    atualizar_categorias_e_tipo(DB_PATH)
