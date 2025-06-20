import sqlite3

def auditoria_colunas_calculadas(db_path='grupo_fisgar.db'):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    print("==== INCONSISTÊNCIAS DE CUSTO ====\n")

    # 1. Produtos processados sem custo_com_ipi
    print("Produtos processados sem custo_com_ipi:")
    cur.execute("""
        SELECT codigo, codigo_fornecedor, nome, data_emissao FROM produtos_processados
        WHERE custo_com_ipi IS NULL OR custo_com_ipi = 0
    """)
    for row in cur.fetchall():
        print(row)

    # 2. Produtos sem custo_com_ipi ou diferente do último custo processado
    print("\nProdutos sem custo_com_ipi ou divergentes:")
    cur.execute("""
        SELECT p.id, p.codigo_fornecedor, p.nome, p.custo_com_ipi, (
            SELECT pp.custo_com_ipi
            FROM produtos_processados pp
            WHERE pp.codigo_fornecedor = p.codigo_fornecedor
              AND pp.custo_com_ipi IS NOT NULL AND pp.custo_com_ipi > 0
            ORDER BY datetime(pp.data_emissao) DESC, pp.codigo DESC
            LIMIT 1
        ) as custo_mais_recente
        FROM produtos p
        WHERE p.custo_com_ipi IS NULL OR ABS(p.custo_com_ipi - custo_mais_recente) > 0.00001
    """)
    for row in cur.fetchall():
        print(row)

    # 3. Estoque sem preco_custo_total ou divergente do último custo processado
    print("\nEstoque sem preco_custo_total ou divergente:")
    cur.execute("""
        SELECT e.id, e.codigo, e.nome, e.preco_custo_total, (
            SELECT pp.custo_com_ipi
            FROM produtos_processados pp
            WHERE pp.codigo_fornecedor = e.codigo
              AND pp.custo_com_ipi IS NOT NULL AND pp.custo_com_ipi > 0
            ORDER BY datetime(pp.data_emissao) DESC, pp.codigo DESC
            LIMIT 1
        ) as custo_mais_recente
        FROM estoque e
        WHERE e.preco_custo_total IS NULL OR ABS(e.preco_custo_total - custo_mais_recente) > 0.00001
    """)
    for row in cur.fetchall():
        print(row)

    # 4. Configurações de unidades sem custo_unitario_real ou divergente do último processado
    print("\nConfigurações de unidade sem custo_unitario_real ou divergente:")
    cur.execute("""
        SELECT c.id, c.codigo_fornecedor, c.nome, c.unidade_compra, c.custo_unitario_real, (
            SELECT pp.custo_com_ipi
            FROM produtos_processados pp
            WHERE pp.codigo_fornecedor = c.codigo_fornecedor
              AND pp.unidade_compra = c.unidade_compra
              AND pp.custo_com_ipi IS NOT NULL AND pp.custo_com_ipi > 0
            ORDER BY datetime(pp.data_emissao) DESC, pp.codigo DESC
            LIMIT 1
        ) as custo_mais_recente
        FROM configuracoes_unidades c
        WHERE c.custo_unitario_real IS NULL OR ABS(c.custo_unitario_real - custo_mais_recente) > 0.00001
    """)
    for row in cur.fetchall():
        print(row)

    conn.close()
    print("\n==== FIM DA AUDITORIA ====\n")

auditoria_colunas_calculadas()
