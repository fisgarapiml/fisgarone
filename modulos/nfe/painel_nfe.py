from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
import sqlite3
import os
import xml.etree.ElementTree as ET
from pathlib import Path

import os
from pathlib import Path

# Pega sempre a raiz do projeto (ajustando caso o script seja movido de pasta)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
XML_DIR = os.path.join(BASE_DIR, '..', '..', 'compras_xml')
XML_DIR = os.path.abspath(XML_DIR)
DB_PATH = os.path.join(BASE_DIR, '..', '..', 'grupo_fisgar.db')
DB_PATH = os.path.abspath(DB_PATH)


# Criação do Blueprint
nfe_bp = Blueprint('nfe', __name__)


def get_db_connection():
    """Estabelece conexão com o banco de dados"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def processar_xmls():
    """Processa todos os XMLs na pasta compras_xml e importa para o banco de dados"""
    xml_files = list(Path(XML_DIR).glob('*.xml'))
    processados = 0

    for xml_file in xml_files:
        conn = None
        try:
            # Parse do XML
            tree = ET.parse(xml_file)
            root = tree.getroot()
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

            # Extração dos dados da NFe
            infNFe = root.find('.//nfe:infNFe', ns)
            ide = infNFe.find('.//nfe:ide', ns)
            emit = infNFe.find('.//nfe:emit', ns)
            total = infNFe.find('.//nfe:total/nfe:ICMSTot', ns)

            numero_nfe = ide.find('.//nfe:nNF', ns).text
            chave_acesso = infNFe.get('Id')[3:]  # Remove 'NFe' do início
            data_emissao = ide.find('.//nfe:dhEmi', ns).text
            cnpj_emitente = emit.find('.//nfe:CNPJ', ns).text
            nome_emitente = emit.find('.//nfe:xNome', ns).text
            valor_total = float(total.find('.//nfe:vNF', ns).text)

            conn = get_db_connection()

            # Verifica se NFe já existe
            existe = conn.execute('SELECT 1 FROM nfe_processadas WHERE numero_nfe = ?', (numero_nfe,)).fetchone()
            if existe:
                continue

            # Insere NFe na tabela
            conn.execute('''
                INSERT INTO nfe_processadas (
                    numero_nfe, chave_acesso, fornecedor, 
                    data_emissao, total_nota, caminho_xml, data_importacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                numero_nfe, chave_acesso, nome_emitente,
                data_emissao, valor_total, str(xml_file), datetime.now().isoformat()
            ))

            # Processa cada produto da NFe
            for det in root.findall('.//nfe:det', ns):
                prod = det.find('.//nfe:prod', ns)
                imposto = det.find('.//nfe:imposto', ns)

                codigo = prod.find('.//nfe:cProd', ns).text
                ean = ''
                if prod.find('.//nfe:cEANTrib', ns) is not None:
                    ean = prod.find('.//nfe:cEANTrib', ns).text
                elif prod.find('.//nfe:cEAN', ns) is not None:
                    ean = prod.find('.//nfe:cEAN', ns).text

                nome = prod.find('.//nfe:xProd', ns).text
                unidade_compra = prod.find('.//nfe:uCom', ns).text
                qtd_comprada = float(prod.find('.//nfe:qCom', ns).text)
                valor_total_item = float(prod.find('.//nfe:vProd', ns).text)
                valor_unitario_nfe = float(prod.find('.//nfe:vUnCom', ns).text)
                ncm = prod.find('.//nfe:NCM', ns).text if prod.find('.//nfe:NCM', ns) is not None else ''
                cest = prod.find('.//nfe:CEST', ns).text if prod.find('.//nfe:CEST', ns) is not None else ''
                cfop = prod.find('.//nfe:CFOP', ns).text if prod.find('.//nfe:CFOP', ns) is not None else ''

                # CST extraído de ICMS se possível
                cst = ''
                icms_node = imposto.find('.//nfe:ICMS', ns)
                if icms_node is not None:
                    for child in icms_node:
                        cst_tag = child.find('.//nfe:CST', ns)
                        if cst_tag is not None:
                            cst = cst_tag.text
                            break

                ipi_percentual = 0
                ipi_valor = 0
                if imposto.find('.//nfe:IPI', ns) is not None:
                    ipi_node = imposto.find('.//nfe:IPI/nfe:IPITrib/nfe:pIPI', ns)
                    ipi_valor_node = imposto.find('.//nfe:IPI/nfe:IPITrib/nfe:vIPI', ns)
                    if ipi_node is not None:
                        try:
                            ipi_percentual = float(ipi_node.text)
                        except Exception:
                            ipi_percentual = 0
                    if ipi_valor_node is not None:
                        try:
                            ipi_valor = float(ipi_valor_node.text)
                        except Exception:
                            ipi_valor = 0

                conn.execute('''
                    INSERT INTO produtos_nfe (
                        codigo, ean, nome, unidade_compra, qtd_comprada, valor_total_item, valor_unitario_nfe,
                        ncm, cest, cfop, cst, ipi_percentual, ipi_valor, fornecedor, codigo_fornecedor,
                        numero_nfe, data_emissao, status, revisado, caminho_xml, data_importacao, observacoes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    codigo, ean, nome, unidade_compra, qtd_comprada, valor_total_item, valor_unitario_nfe,
                    ncm, cest, cfop, cst, ipi_percentual, ipi_valor, nome_emitente, codigo,
                    numero_nfe, data_emissao, 'pendente', 0, str(xml_file), datetime.now().isoformat(), ''
                ))

            conn.commit()
            processados += 1

        except Exception as e:
            print(f"Erro ao processar {xml_file}: {str(e)}")
            continue
        finally:
            if conn:
                conn.close()

    return processados


@nfe_bp.route('/')
def painel():
    """Exibe o painel de NF-e após processar os XMLs"""
    try:
        # Processa XMLs automaticamente antes de exibir
        xml_processados = processar_xmls()
        print(f"{xml_processados} XMLs processados com sucesso")

        conn = get_db_connection()

        # Consulta os produtos pendentes (não finalizados)
        produtos = conn.execute('''
            SELECT * FROM produtos_nfe 
            WHERE status IS NULL OR status != 'finalizado'
            ORDER BY data_emissao DESC
        ''').fetchall()

        # Total de produtos pendentes
        total_produtos = len(produtos)

        # Soma total dos valores
        valor_total = sum(
            float(p['valor_total_item']) for p in produtos if p['valor_total_item'] is not None
        )

        # Listas únicas para filtros
        fornecedores = sorted(set(p['fornecedor'] for p in produtos if p['fornecedor']))
        numeros_nfe = sorted(set(p['numero_nfe'] for p in produtos if p['numero_nfe']))

        return render_template(
            'nfe/painel_nfe.html',
            produtos=produtos,
            total_produtos=total_produtos,
            valor_total=valor_total,
            fornecedores_unicos=fornecedores,
            numeros_nfe=numeros_nfe
        )

    except Exception as e:
        print(f"[ERRO /nfe/painel] {str(e)}")
        return "Erro ao carregar painel de NF-e", 500

    finally:
        if 'conn' in locals():
            conn.close()


@nfe_bp.route('/api/painel')
def painel_api():
    """API que retorna os dados para o painel em formato JSON"""
    conn = get_db_connection()
    try:
        produtos = conn.execute('''
            SELECT * FROM produtos_nfe 
            WHERE status IS NULL OR status != 'finalizado'
        ''').fetchall()

        total_produtos = len(produtos)
        valor_total = sum(float(p['valor_total_item']) for p in produtos if p['valor_total_item'] is not None)

        return jsonify({
            'produtos': [dict(p) for p in produtos],
            'total_produtos': total_produtos or 0,
            'valor_total': valor_total or 0,
            'fornecedores_unicos': list(set(p['fornecedor'] for p in produtos if p['fornecedor'])) or [],
            'numeros_nfe': list(set(p['numero_nfe'] for p in produtos if p['numero_nfe'])) or []
        })
    finally:
        conn.close()

@nfe_bp.route('/salvar-produto', methods=['POST'])
def salvar_produto():
    """Salva as configurações de um produto específico após revisão"""
    data = request.get_json()

    # Validação dos campos obrigatórios
    required_fields = ['id', 'qtd_volumes', 'qtd_por_volume', 'tipo_unidade', 'valor_total_item', 'ipi_percentual']
    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': 'Campos obrigatórios faltando'}), 400

    conn = None
    try:
        conn = get_db_connection()

        # Cálculos dos valores (totalmente baseados nos campos brutos)
        qtd_real_unidades = data['qtd_volumes'] * data['qtd_por_volume']
        custo_volume = data['valor_total_item'] / data['qtd_volumes'] if data['qtd_volumes'] > 0 else 0
        custo_unitario = custo_volume / data['qtd_por_volume'] if data['qtd_por_volume'] > 0 else 0
        custo_com_ipi = custo_unitario * (1 + (data['ipi_percentual'] / 100))

        # Atualização no banco de dados staging
        conn.execute('''
            UPDATE produtos_nfe SET
                qtd_volumes = ?,
                qtd_por_volume = ?,
                qtd_real_unidades = ?,
                custo_volume = ?,
                custo_unitario = ?,
                custo_com_ipi = ?,
                status = 'salvo',
                unidade_compra = ?
            WHERE id = ?
        ''', (
            data['qtd_volumes'],
            data['qtd_por_volume'],
            qtd_real_unidades,
            custo_volume,
            custo_unitario,
            custo_com_ipi,
            data['tipo_unidade'],
            data['id']
        ))

        conn.commit()

        return jsonify({
            'status': 'success',
            'message': 'Produto salvo com sucesso',
            'data': {
                'id': data['id'],
                'qtd_real_unidades': qtd_real_unidades,
                'custo_volume': round(custo_volume, 4),
                'custo_unitario': round(custo_unitario, 4),
                'custo_com_ipi': round(custo_com_ipi, 4)
            }
        })

    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Erro no banco de dados: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro inesperado: {str(e)}'}), 500
    finally:
        if conn:
            conn.close()


@nfe_bp.route('/configurar-unidade', methods=['POST'])
def configurar_unidade():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Dados não fornecidos'}), 400

        required_fields = ['productId', 'codigo_produto', 'tipo_unidade', 'quantidade_por_volume']
        if not all(field in data for field in required_fields):
            return jsonify({'status': 'error', 'message': 'Campos obrigatórios faltando'}), 400

        conn = get_db_connection()

        # Atualiza produto staging
        conn.execute('''
            UPDATE produtos_nfe SET
                unidade_compra = ?,
                qtd_por_volume = ?,
                status = 'configurado'
            WHERE id = ?
        ''', (data['tipo_unidade'], data['quantidade_por_volume'], data['productId']))

        # Atualiza/configura a tabela de conversão (para uso futuro em outras NFe do mesmo produto)
        conn.execute('''
            INSERT OR REPLACE INTO configuracoes_unidade (
                codigo_fornecedor, unidade_compra, qtd_por_volume
            ) VALUES (?, ?, ?)
        ''', (data['codigo_produto'], data['tipo_unidade'], data['quantidade_por_volume']))

        conn.commit()
        return jsonify({
            'status': 'success',
            'message': 'Configuração salva com sucesso',
            'data': data
        })

    except sqlite3.Error as e:
        return jsonify({'status': 'error', 'message': f'Erro no banco: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Erro: {str(e)}'}), 500
    finally:
        if 'conn' in locals():
            conn.close()


@nfe_bp.route('/finalizar-nfe', methods=['POST'])
def finalizar_nfe():
    """Finaliza o processamento de uma NF-e após revisão e aprovação dos itens"""
    data = request.get_json()

    required_fields = ['numero_nfe', 'saved_products']
    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': 'Campos obrigatórios faltando'}), 400

    conn = None
    try:
        conn = get_db_connection()

        # Atualiza status dos produtos na tabela staging
        for product_id in data['saved_products']:
            conn.execute('''
                UPDATE produtos_nfe SET
                    status = 'finalizado'
                WHERE id = ?
            ''', (product_id,))

        # Registra a NF-e como processada (pode trazer info dos próprios itens aprovados)
        if data.get('products') and len(data['products']) > 0:
            produto = data['products'][0]
            conn.execute('''
                INSERT OR REPLACE INTO nfe_processadas (
                    numero_nfe, fornecedor, data_emissao,
                    total_nota, caminho_xml, data_importacao, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                data['numero_nfe'],
                produto.get('fornecedor'),
                produto.get('data_emissao'),
                data.get('total_value', 0),
                produto.get('caminho_xml', ''),
                datetime.now().isoformat(),
                'finalizada'
            ))

        conn.commit()
        return jsonify({
            'status': 'success',
            'message': 'NF-e finalizada com sucesso',
            'nfe': data['numero_nfe']
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()


@nfe_bp.route('/carregar-xml', methods=['POST'])
def carregar_xml():
    """Processa upload de um arquivo XML individual"""
    if 'file' not in request.files:
        return jsonify({'status': 'error', 'message': 'Nenhum arquivo enviado'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'status': 'error', 'message': 'Nome de arquivo inválido'}), 400

    conn = None
    try:
        # Parse do XML
        tree = ET.parse(file)
        root = tree.getroot()
        ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

        # Extração dos dados básicos da NFe
        infNFe = root.find('.//nfe:infNFe', ns)
        ide = infNFe.find('.//nfe:ide', ns)
        emit = infNFe.find('.//nfe:emit', ns)
        total = infNFe.find('.//nfe:total/nfe:ICMSTot', ns)

        numero_nfe = ide.find('.//nfe:nNF', ns).text
        data_emissao = ide.find('.//nfe:dhEmi', ns).text
        cnpj_emitente = emit.find('.//nfe:CNPJ', ns).text
        nome_emitente = emit.find('.//nfe:xNome', ns).text
        valor_total = float(total.find('.//nfe:vNF', ns).text)

        conn = get_db_connection()

        # Verifica se NF-e já existe
        existe = conn.execute('SELECT 1 FROM nfe_processadas WHERE numero_nfe = ?', (numero_nfe,)).fetchone()
        if existe:
            return jsonify({'status': 'error', 'message': 'NF-e já processada anteriormente'}), 400

        # Processa cada produto da NFe
        produtos = []
        for det in root.findall('.//nfe:det', ns):
            prod = det.find('.//nfe:prod', ns)
            imposto = det.find('.//nfe:imposto', ns)

            codigo = prod.find('.//nfe:cProd', ns).text
            nome = prod.find('.//nfe:xProd', ns).text
            quantidade = float(prod.find('.//nfe:qCom', ns).text)
            valor_unitario = float(prod.find('.//nfe:vUnCom', ns).text)
            valor_total_item = float(prod.find('.//nfe:vProd', ns).text)

            # Tratamento do IPI
            ipi = 0
            if imposto.find('.//nfe:IPI', ns) is not None:
                ipi_node = imposto.find('.//nfe:IPI/nfe:IPITrib/nfe:pIPI', ns)
                if ipi_node is not None:
                    ipi = float(ipi_node.text)

            produtos.append({
                'codigo_fornecedor': codigo,
                'nome': nome,
                'quantidade': quantidade,
                'valor_total': valor_total_item,
                'ipi': ipi,
                'fornecedor': nome_emitente,
                'numero_nfe': numero_nfe,
                'data_emissao': data_emissao,
                'caminho_xml': file.filename,
                'status': 'pendente'
            })

        # Insere NF-e na tabela
        conn.execute('''
            INSERT INTO nfe_processadas (
                numero_nfe, fornecedor, data_emissao,
                total_nota, caminho_xml, data_importacao
            ) VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            numero_nfe,
            nome_emitente,
            data_emissao,
            valor_total,
            file.filename,
            datetime.now().isoformat()
        ))

        # Insere cada produto na tabela
        for produto in produtos:
            conn.execute('''
                INSERT INTO produtos_processados (
                    codigo_fornecedor, nome, quantidade, valor_total,
                    ipi, fornecedor, numero_nfe, data_emissao,
                    caminho_xml, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                produto['codigo_fornecedor'],
                produto['nome'],
                produto['quantidade'],
                produto['valor_total'],
                produto['ipi'],
                produto['fornecedor'],
                produto['numero_nfe'],
                produto['data_emissao'],
                produto['caminho_xml'],
                produto['status']
            ))

        conn.commit()
        return jsonify({
            'status': 'success',
            'message': 'XML processado com sucesso',
            'nfe': numero_nfe,
            'total_produtos': len(produtos),
            'valor_total': valor_total
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500
    finally:
        if conn:
            conn.close()

            # ... (código anterior permanece o mesmo até a função carregar_xml)

            # ... (código anterior permanece o mesmo até a função carregar_xml)

            @nfe_bp.route('/api/nfe/import', methods=['GET'])
            def api_nfe_import():
                """API para carregar os dados da NF-e processada com validação dinâmica"""
                conn = None
                try:
                    conn = get_db_connection()

                    # Primeiro processa quaisquer XMLs novos
                    processar_xmls()

                    # Consulta os produtos processados
                    produtos = conn.execute('''
                        SELECT * FROM produtos_nfe 
                        WHERE status IS NULL OR status != 'finalizado'
                        ORDER BY data_emissao DESC
                    ''').fetchall()

                    # Consulta os produtos existentes no sistema para comparação
                    produtos_sistema = conn.execute('''
                        SELECT codigo_barras, descricao, unidade_compra, 
                               custo_unitario, fornecedor_padrao
                        FROM produtos
                    ''').fetchall()

                    # Converter para dicionário por código de barras para fácil acesso
                    produtos_por_codigo = {p['codigo_barras']: dict(p) for p in produtos_sistema}

                    resultados = []
                    fornecedores = set()
                    nfes = set()

                    for produto in produtos:
                        # Identificação do produto no sistema
                        produto_sistema = produtos_por_codigo.get(produto['codigo'])

                        # Classificação dinâmica
                        status = "new"
                        campos_alterados = []
                        custo_alterado = False

                        if produto_sistema:
                            status = "unchanged"
                            # Comparação de campos
                            comparacoes = [
                                ('nome', produto['nome'], produto_sistema['descricao']),
                                ('unidade', produto.get('unidade_compra', 'UN'), produto_sistema['unidade_compra']),
                                ('fornecedor', produto['fornecedor'], produto_sistema['fornecedor_padrao'])
                            ]

                            # Verifica alterações
                            for campo, valor_nfe, valor_sistema in comparacoes:
                                if str(valor_nfe).strip().lower() != str(valor_sistema).strip().lower():
                                    campos_alterados.append({
                                        'campo': campo,
                                        'valor_nfe': valor_nfe,
                                        'valor_sistema': valor_sistema
                                    })
                                    status = "updated"

                            # Verificação especial para custo
                            custo_atual = produto_sistema['custo_unitario']
                            custo_nfe = produto['valor_total_item'] / produto['qtd_comprada'] if produto[
                                                                                                     'qtd_comprada'] > 0 else 0

                            if custo_atual and abs(custo_atual - custo_nfe) / custo_atual > 0.05:  # 5% de variação
                                custo_alterado = True
                                status = "price-change"
                                campos_alterados.append({
                                    'campo': 'custo_unitario',
                                    'valor_nfe': custo_nfe,
                                    'valor_sistema': custo_atual,
                                    'variacao_percentual': ((custo_nfe - custo_atual) / custo_atual) * 100
                                })

                        # Adiciona aos resultados
                        resultados.append({
                            'id': produto['id'],
                            'codigo': produto['codigo'],
                            'nome': produto['nome'],
                            'quantidade': produto['qtd_comprada'],
                            'valor_total': produto['valor_total_item'],
                            'ipi': produto['ipi_percentual'],
                            'fornecedor': produto['fornecedor'],
                            'numero_nfe': produto['numero_nfe'],
                            'data_emissao': produto['data_emissao'],
                            'status': status,
                            'campos_alterados': campos_alterados,
                            'custo_alterado': custo_alterado,
                            'dados_sistema': produto_sistema if produto_sistema else None
                        })

                        # Adiciona aos filtros
                        fornecedores.add(produto['fornecedor'])
                        nfes.add(produto['numero_nfe'])

                    return jsonify({
                        'status': 'success',
                        'data': {
                            'produtos': resultados,
                            'total_produtos': len(resultados),
                            'total_novos': sum(1 for p in resultados if p['status'] == "new"),
                            'total_atualizados': sum(1 for p in resultados if p['status'] == "updated"),
                            'total_custo_alterado': sum(1 for p in resultados if p['status'] == "price-change"),
                            'total_inalterados': sum(1 for p in resultados if p['status'] == "unchanged"),
                            'fornecedores': sorted(fornecedores),
                            'nfes': sorted(nfes)
                        }
                    })

                except Exception as e:
                    return jsonify({'status': 'error', 'message': str(e)}), 500
                finally:
                    if conn:
                        conn.close()

            @nfe_bp.route('/api/nfe/confirm', methods=['POST'])
            def api_nfe_confirm():
                """API para confirmar a importação dos itens selecionados"""
                data = request.get_json()

                if not data or 'itens' not in data:
                    return jsonify({'status': 'error', 'message': 'Dados inválidos'}), 400

                conn = None
                try:
                    conn = get_db_connection()
                    resultados = {
                        'sucesso': [],
                        'erros': [],
                        'atualizados': 0,
                        'novos': 0
                    }

                    for item in data['itens']:
                        try:
                            produto = conn.execute('''
                                SELECT * FROM produtos_nfe WHERE id = ?
                            ''', (item['id'],)).fetchone()

                            if not produto:
                                resultados['erros'].append({
                                    'id': item['id'],
                                    'message': 'Produto não encontrado'
                                })
                                continue

                            custo_unitario = produto['valor_total_item'] / produto['qtd_comprada'] if produto[
                                                                                                          'qtd_comprada'] > 0 else 0

                            if item['status'] == 'new':
                                conn.execute('''
                                    INSERT INTO produtos (
                                        codigo_barras, descricao, unidade_compra,
                                        custo_unitario, fornecedor_padrao, data_cadastro
                                    ) VALUES (?, ?, ?, ?, ?, ?)
                                ''', (
                                    produto['codigo'],
                                    produto['nome'],
                                    produto.get('unidade_compra', 'UN'),
                                    custo_unitario,
                                    produto['fornecedor'],
                                    datetime.now().isoformat()
                                ))
                                resultados['novos'] += 1

                            elif item['status'] in ['updated', 'price-change']:
                                conn.execute('''
                                    UPDATE produtos SET
                                        descricao = ?,
                                        unidade_compra = ?,
                                        custo_unitario = ?,
                                        fornecedor_padrao = ?,
                                        data_atualizacao = ?
                                    WHERE codigo_barras = ?
                                ''', (
                                    produto['nome'],
                                    produto.get('unidade_compra', 'UN'),
                                    custo_unitario,
                                    produto['fornecedor'],
                                    datetime.now().isoformat(),
                                    produto['codigo']
                                ))
                                resultados['atualizados'] += 1

                            conn.execute('''
                                UPDATE produtos_nfe SET
                                    status = 'finalizado',
                                    data_importacao = ?
                                WHERE id = ?
                            ''', (datetime.now().isoformat(), produto['id']))

                            resultados['sucesso'].append({
                                'id': item['id'],
                                'codigo': produto['codigo'],
                                'nome': produto['nome'],
                                'status': item['status']
                            })

                        except Exception as e:
                            resultados['erros'].append({
                                'id': item.get('id'),
                                'message': str(e)
                            })

                    if resultados['sucesso']:
                        nfe = resultados['sucesso'][0].get('numero_nfe')
                        if nfe:
                            conn.execute('''
                                UPDATE nfe_processadas SET
                                    status = 'processada',
                                    data_processamento = ?
                                WHERE numero_nfe = ?
                            ''', (datetime.now().isoformat(), nfe))

                    conn.commit()

                    return jsonify({
                        'status': 'success',
                        'resultados': resultados,
                        'message': f"Processados: {len(resultados['sucesso'])} itens | Erros: {len(resultados['erros'])}"
                    })

                except Exception as e:
                    return jsonify({'status': 'error', 'message': str(e)}), 500
                finally:
                    if conn:
                        conn.close()

            # Corrigindo a rota principal para usar o template correto
            @nfe_bp.route('/nfe')
            def painel():
                try:
                    # Debug: Verificar caminhos
                    print(f"XML_DIR: {XML_DIR}")
                    print(f"DB_PATH: {DB_PATH}")

                    xml_processados = processar_xmls()
                    print(f"{xml_processados} XMLs processados")

                    conn = get_db_connection()
                    produtos = conn.execute(
                        'SELECT * FROM produtos_nfe WHERE status IS NULL OR status != "finalizado"').fetchall()

                    return render_template(
                        'nfe/painel_nfe.html',
                        produtos=produtos,
                        total_produtos=len(produtos),
                        valor_total=sum(float(p['valor_total_item']) for p in produtos if p['valor_total_item']),
                        fornecedores_unicos=sorted(set(p['fornecedor'] for p in produtos if p['fornecedor'])),
                        numeros_nfe=sorted(set(p['numero_nfe'] for p in produtos if p['numero_nfe']))
                    )
                except Exception as e:
                    print(f"ERRO: {str(e)}")
                    return render_template('nfe/erro.html', mensagem=str(e)), 500
                finally:
                    if 'conn' in locals():
                        conn.close()

