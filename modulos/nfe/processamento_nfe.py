import os
import sqlite3
from xml.etree import ElementTree as ET
from datetime import datetime
import xml.dom.minidom


def processar_xmls(pasta_xml, caminho_db):
    xmls_processados = []

    def obter_dados_nfe(caminho_db, filtro=None, valor=None):
        try:
            conn = sqlite3.connect(caminho_db)
            cursor = conn.cursor()

            # Verifica se a tabela existe
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='nfe'")
            if not cursor.fetchone():
                raise ValueError("Tabela 'nfe' não encontrada no banco de dados")

            # Sua lógica de consulta original aqui
            # ...

        except sqlite3.Error as e:
            raise ValueError(f"Erro no banco de dados: {str(e)}")
        finally:
            if conn:
                conn.close()

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

    return xmls_processados


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
        inseridos = 0
        for prod in produtos:
            # Checa se já existe este produto da mesma NF-e
            nfe_chave = prod.get('nfe_chave')
            codigo = prod.get('codigo')
            cursor.execute(
                "SELECT 1 FROM produtos_nfe WHERE nfe_chave = ? AND codigo = ?",
                (nfe_chave, codigo)
            )
            if cursor.fetchone():
                continue  # Já existe, não insere de novo

            # Insere no banco
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
            inseridos += 1

        conn.commit()
        if inseridos == 0:
            return {'status': 'info', 'message': 'Nenhum produto novo para cadastrar (todos já existem)'}
        return {'status': 'success', 'message': f'{inseridos} produto(s) cadastrado(s) com sucesso'}
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