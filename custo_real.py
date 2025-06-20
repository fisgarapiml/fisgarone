import sqlite3

DB_PATH = 'grupo_fisgar.db'

def buscar_configuracao(cur, codigo_fornecedor, unidade_compra):
    cur.execute("""
        SELECT qtd_por_volume, qtd_por_pacote
        FROM configuracoes_unidades
        WHERE codigo_fornecedor = ? AND unidade_compra = ? AND ativo = 1
        ORDER BY atualizado_em DESC LIMIT 1
    """, (codigo_fornecedor, unidade_compra))
    row = cur.fetchone()
    if row:
        qtd_por_volume = int(row[0]) if row[0] else 1
        qtd_por_pacote = int(row[1]) if row[1] else 1
        return qtd_por_volume, qtd_por_pacote
    return None, None

def inserir_produtos_processados_sem_duplicidade(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    inseridos = 0
    pulados = []

    cur.execute("""
        SELECT 
            pn.codigo as codigo_fornecedor, pn.descricao as nome, pn.unidade, 
            pn.quantidade, pn.valor_total, pn.ipi, pn.fornecedor, pn.numero, pn.data_emissao, 
            pn.nfe_chave, pn.cnpj_emitente
        FROM produtos_nfe pn
    """)

    rows = cur.fetchall()

    for row in rows:
        (codigo_fornecedor, nome, unidade_compra, quantidade, valor_total, ipi,
         fornecedor, numero_nfe, data_emissao, caminho_xml, cnpj_emitente) = row

        # --- Verifica duplicidade para produto na mesma NF-e e unidade ---
        cur.execute("""
            SELECT 1 FROM produtos_processados
            WHERE codigo_fornecedor = ? AND numero_nfe = ? AND unidade_compra = ?
        """, (codigo_fornecedor, numero_nfe, unidade_compra))
        if cur.fetchone():
            continue  # Já existe esta combinação nesta nota e unidade, não insere de novo

        qtd_por_volume, qtd_por_pacote = buscar_configuracao(cur, codigo_fornecedor, unidade_compra)
        if not qtd_por_volume or not qtd_por_pacote:
            pulados.append((codigo_fornecedor, unidade_compra, "SEM configuração de unidade"))
            continue

        try:
            qtd_volumes = int(quantidade) if quantidade is not None else 1
            qtd_real_unidades = qtd_volumes * qtd_por_volume * qtd_por_pacote
            custo_volume = float(valor_total) / qtd_volumes if qtd_volumes else 0.0
            custo_unitario = float(valor_total) / qtd_real_unidades if qtd_real_unidades else 0.0
            ipi_valor = float(ipi) if ipi is not None else 0.0

            percentual_ipi = ipi_valor / float(valor_total) if valor_total else 0.0
            custo_com_ipi = custo_unitario * (1 + percentual_ipi)

            cur.execute("""
                INSERT INTO produtos_processados (
                    codigo_fornecedor, nome, unidade_compra, quantidade, valor_total, ipi,
                    qtd_volumes, qtd_por_volume, qtd_real_unidades, custo_volume, custo_unitario,
                    custo_com_ipi, fornecedor, numero_nfe, data_emissao, caminho_xml,
                    novo, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                codigo_fornecedor, nome, unidade_compra, quantidade, valor_total, ipi_valor,
                qtd_volumes, qtd_por_volume, qtd_real_unidades, custo_volume, custo_unitario,
                custo_com_ipi, fornecedor, numero_nfe, data_emissao, caminho_xml,
                '0', 'sincronizado'
            ))
            inseridos += 1
        except Exception as e:
            pulados.append((codigo_fornecedor, unidade_compra, str(e)))

    conn.commit()
    conn.close()
    print(f"✅ {inseridos} produtos inseridos em produtos_processados (sem duplicidade por produto, nota e unidade).")
    if pulados:
        print("⚠️ Não inseridos (corrija no configuracoes_unidades):")
        for info in pulados:
            print(" -", info)

if __name__ == '__main__':
    inserir_produtos_processados_sem_duplicidade()
