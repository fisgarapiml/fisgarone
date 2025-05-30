import os
import sqlite3
from xml.etree import ElementTree as ET
from datetime import datetime


def consolidar_estoque_produtos_nfe():
    DB = 'grupo_fisgar.db'
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()

        # Busca todos os códigos únicos presentes em produtos_nfe
        cur.execute("SELECT DISTINCT codigo FROM produtos_nfe")
        codigos = [row[0] for row in cur.fetchall()]

        for codigo in codigos:
            # Busca todos os lançamentos desse código, qualquer unidade
            cur.execute("""
                SELECT unidade, SUM(quantidade) AS qtd_total, SUM(valor_total) AS valor_total,
                       MAX(descricao) AS nome, MAX(fornecedor) AS fornecedor, MAX(ncm) AS ncm
                FROM produtos_nfe
                WHERE codigo = ?
                GROUP BY unidade
            """, (codigo,))
            lancamentos = cur.fetchall()

            qtd_final = 0
            valor_final = 0

            for (unidade, qtd_total, valor_total, nome, fornecedor, ncm) in lancamentos:
                # Busca fator de conversão para unidade (deve existir!)
                cur.execute("""
                    SELECT COALESCE(qtd_por_volume, 1) * COALESCE(qtd_por_pacote, 1)
                    FROM configuracoes_unidades
                    WHERE codigo_fornecedor = ? AND unidade_compra = ?
                """, (codigo, unidade))
                fator_row = cur.fetchone()
                fator = fator_row[0] if fator_row and fator_row[0] else 1

                # Converte a quantidade total para peças/fracionada
                qtd_fracionada = (qtd_total or 0) * fator

                qtd_final += qtd_fracionada
                valor_final += (valor_total or 0)

            # Calcula o custo unitário final
            custo_unitario = valor_final / qtd_final if qtd_final else 0

            # Busca SKU existente no estoque (se houver), para manter (NUNCA gerar aleatório)
            cur.execute("SELECT sku FROM estoque WHERE codigo = ? LIMIT 1", (codigo,))
            sku_existente = cur.fetchone()
            sku_final = sku_existente[0] if sku_existente else None

            # Monta dados para atualizar/inserir no estoque
            data = (
                sku_final,  # SKU atual, pode estar vazio (será preenchido depois)
                codigo,
                nome,
                'PC',  # Unidade consolidada sempre em peça/fracionada
                qtd_final,
                custo_unitario,
                fornecedor,
                ncm
            )

            # Verifica se já existe o produto no estoque (por codigo)
            cur.execute("SELECT 1 FROM estoque WHERE codigo = ?", (codigo,))
            if cur.fetchone():
                # Atualiza dados
                cur.execute("""
                    UPDATE estoque
                    SET sku = ?, nome = ?, unidade = ?, qtd_estoque = ?, custo_unitario = ?, fornecedor_padrao = ?, ncm = ?, data_atualizacao = datetime('now','localtime')
                    WHERE codigo = ?
                """, (sku_final, nome, 'PC', qtd_final, custo_unitario, fornecedor, ncm, codigo))
            else:
                # Insere novo registro
                cur.execute("""
                    INSERT INTO estoque (sku, codigo, nome, unidade, qtd_estoque, custo_unitario, fornecedor_padrao, ncm, data_cadastro, data_atualizacao)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'), datetime('now','localtime'))
                """, data)

        conn.commit()
        print('✅ Estoque consolidado com segurança, 1 linha por código, custo correto, SKU preservado!')


def processar_xmls(pasta_xml, caminho_db):
    xmls_processados = []

    for arquivo in os.listdir(pasta_xml):
        if arquivo.endswith('.xml'):
            caminho_xml = os.path.join(pasta_xml, arquivo)
            try:
                dados_nfe = extrair_dados_xml(caminho_xml)
                salvar_nfe_db(caminho_db, dados_nfe)

                # CONSOLIDAÇÃO AUTOMÁTICA DO ESTOQUE AQUI
                consolidar_estoque_produtos_nfe()  # Chama sempre após importar produtos da nota

                xmls_processados.append({
                    'chave': dados_nfe[0]['nfe_chave'] if dados_nfe else '',
                    'fornecedor': dados_nfe[0]['fornecedor'] if dados_nfe else '',
                    'data_emissao': dados_nfe[0]['data_emissao'] if dados_nfe else '',
                    'valor_total': sum([p['valor_total'] for p in dados_nfe]) if dados_nfe else 0,
                    'status': 'Processado'
                })
            except Exception as e:
                xmls_processados.append({
                    'arquivo': arquivo,
                    'status': f'Erro: {str(e)}'
                })

    return xmls_processados

# Mantém suas funções extrair_dados_xml e salvar_nfe_db do jeito que já estão aí em cima!
# Não mude nada nelas.

# Como usar:
# Exemplo de chamada:
# processar_xmls('C:/fisgarone/xmls', 'C:/fisgarone/grupo_fisgar.db')

