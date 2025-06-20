import os
import sqlite3
from xml.etree import ElementTree as ET
from datetime import datetime
import xml.dom.minidom


def processar_xmls(pasta_xml, caminho_db):
    xmls_processados = []

    # 1. Processa os XMLs normalmente
    for arquivo in os.listdir(pasta_xml):
        if arquivo.endswith('.xml'):
            caminho_xml = os.path.join(pasta_xml, arquivo)
            try:
                dados_nfe = extrair_dados_xml(caminho_xml)
                salvar_nfe_db(caminho_db, dados_nfe)
                xmls_processados.append({
                    'chave': dados_nfe['chave'],
                    'fornecedor': dados_nfe['emitente']['nome'],
                    'data_emissao': dados_nfe['data_emissao'],
                    'valor_total': dados_nfe['valor_total'],
                    'status': 'Processado'
                })
            except Exception as e:
                xmls_processados.append({
                    'arquivo': arquivo,
                    'status': f'Erro: {str(e)}'
                })

    # 2. Atualiza o estoque com verificação segura
    try:
        consolidar_estoque_produtos_nfe_seguro(caminho_db)
    except Exception as e:
        print(f"Erro ao atualizar estoque: {str(e)}")

    return xmls_processados


def consolidar_estoque_produtos_nfe_seguro(caminho_db):
    """Versão segura que verifica as colunas antes de operar"""
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    try:
        # Verifica se as colunas existem
        cursor.execute("PRAGMA table_info(estoque)")
        colunas = [info[1] for info in cursor.fetchall()]

        colunas_necessarias = {'percentual_ipi', 'preco_custo_total'}
        colunas_faltantes = colunas_necessarias - set(colunas)

        if colunas_faltantes:
            raise Exception(f"Colunas faltantes no banco: {', '.join(colunas_faltantes)}. "
                            f"Execute manualmente: ALTER TABLE estoque ADD COLUMN percentual_ipi REAL DEFAULT 0; "
                            f"ALTER TABLE estoque ADD COLUMN preco_custo_total REAL DEFAULT 0;")

        # Consulta segura usando apenas colunas existentes
        cursor.execute("""
            WITH dados_produtos AS (
                SELECT 
                    codigo,
                    MAX(descricao) as descricao,
                    MAX(fornecedor) as fornecedor,
                    MAX(ncm) as ncm,
                    SUM(quantidade) as quantidade_total,
                    SUM(valor_total) as valor_total,
                    SUM(ipi) as ipi_total
                FROM produtos_nfe
                GROUP BY codigo
            )
            INSERT OR REPLACE INTO estoque (
                codigo, nome, unidade, qtd_estoque, custo_unitario,
                percentual_ipi, preco_custo_total, fornecedor_padrao, ncm,
                data_atualizacao
            )
            SELECT 
                codigo,
                descricao,
                'PC',
                quantidade_total,
                CASE WHEN quantidade_total > 0 THEN valor_total / quantidade_total ELSE 0 END,
                CASE WHEN valor_total > 0 THEN (ipi_total / valor_total) * 100 ELSE 0 END,
                CASE WHEN quantidade_total > 0 THEN 
                    (valor_total / quantidade_total) * (1 + (ipi_total / valor_total)) 
                ELSE 0 END,
                fornecedor,
                ncm,
                datetime('now')
            FROM dados_produtos
        """)

        conn.commit()
        print(f"✅ Estoque atualizado com sucesso! {cursor.rowcount} itens processados.")
    except Exception as e:
        conn.rollback()
        print(f"❌ Erro ao atualizar estoque: {str(e)}")
    finally:
        conn.close()


def verificar_dados_seguro(caminho_db):
    """Função de verificação segura"""
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    try:
        # Verifica se as colunas existem antes de consultar
        cursor.execute("PRAGMA table_info(estoque)")
        colunas = [info[1] for info in cursor.fetchall()]

        if 'percentual_ipi' not in colunas or 'preco_custo_total' not in colunas:
            print("⚠️ Colunas não existem no banco. Execute os comandos ALTER TABLE primeiro.")
            return

        cursor.execute("SELECT codigo, percentual_ipi, preco_custo_total FROM estoque LIMIT 5")
        print("\n📋 Dados de exemplo do estoque:")
        for row in cursor.fetchall():
            print(row)
    except Exception as e:
        print(f"Erro ao verificar dados: {str(e)}")
    finally:
        conn.close()
def extrair_dados_xml(caminho_xml):
    try:
        tree = ET.parse(caminho_xml)
        root = tree.getroot()
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

        infNFe = root.find('.//nfe:infNFe', ns)
        ide = infNFe.find('nfe:ide', ns)
        emit = infNFe.find('nfe:emit', ns)
        total = infNFe.find('nfe:total/nfe:ICMSTot', ns)

        # Dados fixos da NF-e
        nfe_chave = infNFe.attrib['Id'][3:]
        numero = ide.find('nfe:nNF', ns).text
        serie = ide.find('nfe:serie', ns).text
        data_emissao_raw = ide.find('nfe:dhEmi', ns).text
        data_emissao = datetime.strptime(data_emissao_raw[:19], '%Y-%m-%dT%H:%M:%S').strftime('%d/%m/%Y %H:%M')
        modelo = ide.find('nfe:mod', ns).text
        valor_total = float(total.find('nfe:vNF', ns).text)
        fornecedor = emit.find('nfe:xNome', ns).text
        cnpj_emitente = emit.find('nfe:CNPJ', ns).text

        # Lista de produtos formatada
        produtos = []
        for det in infNFe.findall('nfe:det', ns):
            prod = det.find('nfe:prod', ns)
            imposto = det.find('nfe:imposto', ns)

            produto = {
                'nfe_chave': nfe_chave,
                'numero': numero,
                'fornecedor': fornecedor,
                'data_emissao': data_emissao,
                'descricao': prod.find('nfe:xProd', ns).text,
                'codigo': prod.find('nfe:cProd', ns).text,
                'ncm': prod.find('nfe:NCM', ns).text,
                'quantidade': float(prod.find('nfe:qCom', ns).text),
                'unidade': prod.find('nfe:uCom', ns).text,
                'valor_unitario': float(prod.find('nfe:vUnCom', ns).text),
                'valor_total': float(prod.find('nfe:vProd', ns).text),
                'ipi': (
                    float(imposto.find('nfe:IPI/nfe:IPITrib/nfe:vIPI', ns).text)
                    if imposto.find('nfe:IPI/nfe:IPITrib/nfe:vIPI', ns) is not None else 0.0
                ),
                'st': (
                    float(imposto.find('nfe:ICMS/nfe:ICMS00/nfe:vICMSST', ns).text)
                    if imposto.find('nfe:ICMS/nfe:ICMS00/nfe:vICMSST', ns) is not None else 0.0
                ),
                'serie': serie,
                'modelo': modelo,
                'cnpj_emitente': cnpj_emitente
            }
            produtos.append(produto)
        return produtos
    except Exception as e:
        raise Exception(f"Erro ao processar XML: {str(e)}")


def salvar_nfe_db(caminho_db, produtos):
    """
    Salva os produtos extraídos do XML de NF-e na tabela produtos_nfe.
    Evita duplicidade usando nfe_chave + codigo.
    E alimenta automaticamente a tabela produtos_processados para produtos com configuração.
    Retorna status e mensagem clara para o frontend.

    Parâmetros:
        caminho_db (str): Caminho absoluto do banco SQLite.
        produtos (list): Lista de dicionários, cada um com os dados de um produto.

    Exemplo de item:
        {
            'nfe_chave': '1234...',
            'numero': '123',
            'fornecedor': 'NOME',
            'data_emissao': '25/05/2025',
            'descricao': 'Produto X',
            'codigo': 'SKU123',
            'ncm': '12345678',
            'quantidade': 10,
            'unidade': 'UN',
            'valor_unitario': 1.99,
            'valor_total': 19.90,
            'ipi': 0.0,
            'st': 0.0,
            'serie': '1',
            'modelo': '55',
            'cnpj_emitente': '12345678000199'
        }
    """
    import sqlite3
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    # Garante que sempre será uma lista de dicts
    if isinstance(produtos, dict):
        produtos = [produtos]
    if not isinstance(produtos, list):
        raise Exception("produtos deve ser uma lista de dicionários")

    try:
        inseridos_nfe = 0
        for prod in produtos:
            nfe_chave = prod.get('nfe_chave')
            codigo = prod.get('codigo')
            unidade = prod.get('unidade')
            descricao = prod.get('descricao')

            # Verifica duplicidade considerando unidade e descrição
            cursor.execute(
                "SELECT 1 FROM produtos_nfe WHERE nfe_chave = ? AND codigo = ? AND unidade = ? AND descricao = ?",
                (nfe_chave, codigo, unidade, descricao)
            )
            if cursor.fetchone():
                continue  # Já existe, não insere de novo

            # Insere normalmente:
            cursor.execute("""
                INSERT INTO produtos_nfe (
                    nfe_chave, numero, fornecedor, data_emissao, descricao,
                    codigo, ncm, quantidade, unidade, valor_unitario, valor_total,
                    ipi, st, serie, modelo, cnpj_emitente
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                prod.get('nfe_chave'),
                prod.get('numero'),
                prod.get('fornecedor'),
                prod.get('data_emissao'),
                prod.get('descricao'),
                prod.get('codigo'),
                prod.get('ncm'),
                prod.get('quantidade'),
                prod.get('unidade'),
                prod.get('valor_unitario'),
                prod.get('valor_total'),
                prod.get('ipi'),
                prod.get('st'),
                prod.get('serie'),
                prod.get('modelo'),
                prod.get('cnpj_emitente')
            ))
            inseridos_nfe += 1

        conn.commit()

        # === NOVO BLOCO: Alimenta produtos_processados ===
        try:
            if produtos and 'numero' in produtos[0]:
                numero_nfe = produtos[0]['numero']
                inseridos_pp, pulados = 0, []
                for prod in produtos:
                    codigo_fornecedor = prod.get('codigo')
                    unidade_compra = prod.get('unidade')
                    nome = prod.get('descricao')
                    quantidade = prod.get('quantidade')
                    valor_total = prod.get('valor_total')
                    ipi = prod.get('ipi')
                    fornecedor = prod.get('fornecedor')
                    data_emissao = prod.get('data_emissao')
                    caminho_xml = prod.get('nfe_chave')

                    # Busca configuração de unidade
                    cursor.execute("""
                        SELECT qtd_por_volume, qtd_por_pacote
                        FROM configuracoes_unidades
                        WHERE codigo_fornecedor = ? AND unidade_compra = ? AND ativo = 1
                        ORDER BY atualizado_em DESC LIMIT 1
                    """, (codigo_fornecedor, unidade_compra))
                    config = cursor.fetchone()
                    if not config:
                        pulados.append((codigo_fornecedor, unidade_compra, 'SEM configuração de unidade'))
                        continue

                    qtd_por_volume = int(config[0]) if config[0] else 1
                    qtd_por_pacote = int(config[1]) if config[1] else 1
                    qtd_volumes = int(quantidade) if quantidade else 1
                    qtd_real_unidades = qtd_volumes * qtd_por_volume * qtd_por_pacote
                    custo_volume = float(valor_total) / qtd_volumes if qtd_volumes else 0.0
                    custo_unitario = float(valor_total) / qtd_real_unidades if qtd_real_unidades else 0.0
                    ipi_valor = float(ipi) if ipi else 0.0
                    percentual_ipi = ipi_valor / float(valor_total) if valor_total else 0.0
                    custo_com_ipi = custo_unitario * (1 + percentual_ipi)

                    # Proteção contra duplicidade
                    cursor.execute("""
                        SELECT 1 FROM produtos_processados
                        WHERE codigo_fornecedor = ? AND numero_nfe = ? AND unidade_compra = ?
                    """, (codigo_fornecedor, numero_nfe))
                    if cursor.fetchone():
                        continue

                    cursor.execute("""
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
                    inseridos_pp += 1

                if inseridos_pp > 0:
                    print(f"✅ {inseridos_pp} produtos alimentados automaticamente em produtos_processados.")
                if pulados:
                    print("⚠️ Produtos NÃO alimentados por falta de configuração:")
                    for info in pulados:
                        print("  -", info)
        except Exception as e:
            print(f"[ATENÇÃO] Falha ao alimentar produtos_processados: {e}")
        # === FIM DO BLOCO ===

        if inseridos_nfe == 0:
            return {'status': 'info', 'message': 'Nenhum produto novo para cadastrar (todos já existem)'}
        return {'status': 'success', 'message': f'{inseridos_nfe} produto(s) cadastrado(s) com sucesso'}
    except Exception as e:
        conn.rollback()
        raise Exception(f"Erro ao salvar no banco de dados: {str(e)}")
    finally:
        conn.close()

def obter_dados_nfe(caminho_db, filtro=None, valor=None):
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    try:
        query = '''
            SELECT 
                nfe.chave, nfe.numero, nfe.serie, nfe.data_emissao, nfe.modelo, nfe.valor_total,
                nfe.emitente_nome, nfe.emitente_cnpj,
                COUNT(produtos_nfe.id) as total_produtos,
                SUM(produtos_nfe.quantidade) as total_itens
            FROM nfe
            LEFT JOIN produtos_nfe ON nfe.chave = produtos_nfe.nfe_chave
        '''

        params = []
        if filtro and valor:
            if filtro == 'fornecedor':
                query += ' WHERE nfe.emitente_nome LIKE ?'
                params.append(f'%{valor}%')
            elif filtro == 'numero':
                query += ' WHERE nfe.numero = ?'
                params.append(valor)
            elif filtro == 'chave':
                query += ' WHERE nfe.chave = ?'
                params.append(valor)
            elif filtro == 'data':
                query += ' WHERE DATE(nfe.data_emissao) = ?'
                params.append(valor)

        query += ' GROUP BY nfe.chave ORDER BY nfe.data_emissao DESC'

        cursor.execute(query, params)
        colunas = [desc[0] for desc in cursor.description]
        resultados = [dict(zip(colunas, row)) for row in cursor.fetchall()]

        return resultados
    except Exception as e:
        raise Exception(f"Erro ao obter dados: {str(e)}")
    finally:
        conn.close()


def consolidar_estoque_produtos_nfe():
    import sqlite3

    DB = 'grupo_fisgar.db'
    conn = sqlite3.connect(DB)
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT codigo FROM produtos_nfe")
    codigos = [row[0] for row in cur.fetchall()]

    for codigo in codigos:
        cur.execute("""
            SELECT unidade, SUM(quantidade) as qtd_total, SUM(valor_total) as valor_total,
                   MAX(descricao) as nome, MAX(fornecedor) as fornecedor, MAX(ncm) as ncm
            FROM produtos_nfe
            WHERE codigo = ?
            GROUP BY unidade
        """, (codigo,))
        lancamentos = cur.fetchall()

        qtd_final = 0
        valor_final = 0
        ipi_total = 0  # Soma dos valores de IPI para esse código

        for (unidade, qtd_total, valor_total, nome, fornecedor, ncm) in lancamentos:
            cur.execute("""
                SELECT COALESCE(qtd_por_volume, 1) * COALESCE(qtd_por_pacote, 1)
                FROM configuracoes_unidades
                WHERE codigo_fornecedor = ? AND unidade_compra = ?
            """, (codigo, unidade))
            fator_row = cur.fetchone()
            fator = fator_row[0] if fator_row and fator_row[0] else 1

            qtd_fracionada = (qtd_total or 0) * fator
            qtd_final += qtd_fracionada
            valor_final += (valor_total or 0)

            # Agora busca todas as linhas dessa unidade/codigo para somar o ipi proporcional
            cur.execute("""
                SELECT ipi, quantidade FROM produtos_nfe WHERE codigo = ? AND unidade = ?
            """, (codigo, unidade))
            for ipi_reais, qtd in cur.fetchall():
                if qtd and qtd > 0 and ipi_reais is not None:
                    # Fraciona o IPI por unidade real
                    ipi_total += (ipi_reais / (qtd * fator))

        custo_unitario = round(valor_final / qtd_final, 3) if qtd_final else 0
        preco_custo_total = round(custo_unitario + ipi_total, 3)  # Soma o IPI proporcional por unidade

        # Busca SKU existente OU gera temporário
        cur.execute("SELECT sku FROM estoque WHERE codigo = ? LIMIT 1", (codigo,))
        sku_existente = cur.fetchone()
        sku_final = sku_existente[0] if sku_existente and sku_existente[0] else f'SKU_{codigo}'

        # INSERE/ATUALIZA sempre na unidade PC consolidada!
        cur.execute("SELECT 1 FROM estoque WHERE codigo = ? AND unidade = ?", (codigo, 'PC'))
        if cur.fetchone():
            cur.execute("""
                UPDATE estoque
                SET sku = ?, nome = ?, unidade = ?, qtd_estoque = ?, custo_unitario = ?, fornecedor_padrao = ?, ncm = ?, 
                    preco_custo_total = ?, data_atualizacao = datetime('now','localtime')
                WHERE codigo = ? AND unidade = ?
            """, (sku_final, nome, 'PC', int(qtd_final), custo_unitario, fornecedor, ncm,
                  preco_custo_total, codigo, 'PC'))
        else:
            cur.execute("""
                INSERT INTO estoque (
                    sku, codigo, nome, unidade, qtd_estoque, custo_unitario, fornecedor_padrao, ncm,
                    preco_custo_total, data_cadastro, data_atualizacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'), datetime('now','localtime'))
            """, (sku_final, codigo, nome, 'PC', int(qtd_final), custo_unitario, fornecedor, ncm,
                  preco_custo_total))

    conn.commit()
    conn.close()
    print('✅ Estoque consolidado com custo total (incluindo IPI por unidade)!')

def cadastrar_produtos_nfe(caminho_db, chave_nfe):
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()

    try:
        # Obter produtos da NF-e
        cursor.execute('''
            SELECT codigo, descricao, unidade, quantidade, valor_unitario, ncm
            FROM produtos_nfe WHERE nfe_chave = ?
        ''', (chave_nfe,))
        produtos = cursor.fetchall()

        if not produtos:
            return {'status': 'error', 'message': 'Nenhum produto encontrado para esta NF-e'}

        # Cadastrar cada produto no estoque
        for produto in produtos:
            codigo, descricao, unidade, quantidade, valor_unitario, ncm = produto

            # Verifica se o produto já existe no estoque
            cursor.execute('SELECT id FROM estoque WHERE codigo = ?', (codigo,))
            produto_existente = cursor.fetchone()

            if produto_existente:
                # Atualiza quantidade e valor médio
                cursor.execute('''
                    UPDATE estoque 
                    SET quantidade = quantidade + ?, 
                        valor_medio = ((valor_medio * quantidade) + (? * ?)) / (quantidade + ?),
                        data_atualizacao = CURRENT_TIMESTAMP
                    WHERE codigo = ?
                ''', (quantidade, valor_unitario, quantidade, quantidade, codigo))
            else:
                # Insere novo produto
                cursor.execute('''
                    INSERT INTO estoque (
                        codigo, descricao, unidade, quantidade, valor_medio, ncm,
                        data_cadastro, data_atualizacao
                    ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                ''', (codigo, descricao, unidade, quantidade, valor_unitario, ncm))

        # Marcar NF-e como processada no estoque
        cursor.execute('''
            UPDATE nfe SET processada_estoque = 1 WHERE chave = ?
        ''', (chave_nfe,))

        conn.commit()
        return {'status': 'success', 'message': 'Produtos cadastrados no estoque com sucesso'}
    except Exception as e:
        conn.rollback()
        raise Exception(f"Erro ao cadastrar produtos no estoque: {str(e)}")
    finally:
        conn.close()
