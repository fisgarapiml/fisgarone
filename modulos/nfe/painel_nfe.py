from flask import Blueprint, request, jsonify, render_template
from datetime import datetime
import sqlite3
import os
import xml.etree.ElementTree as ET
from pathlib import Path

# Configurações
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
XML_DIR = os.path.join(BASE_DIR, 'compras_xml')
DB_PATH = os.path.join(BASE_DIR, 'grupo_fisgar.db')

# Criação do Blueprint
nfe_bp = Blueprint('nfe', __name__, url_prefix='/nfe')


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

                # Insere produto na tabela
                conn.execute('''
                    INSERT INTO produtos_processados (
                        codigo_fornecedor, nome, unidade_compra, quantidade,
                        valor_total, ipi, fornecedor, numero_nfe,
                        data_emissao, caminho_xml, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    codigo, nome, 'UN', quantidade,
                    valor_total_item, ipi, nome_emitente, numero_nfe,
                    data_emissao, str(xml_file), 'pendente'
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


@nfe_bp.route('/painel')
def painel():
    """Rota principal que exibe o painel de NFe"""
    # Processa XMLs antes de mostrar o painel
    xml_processados = processar_xmls()
    print(f"Processados {xml_processados} novos XMLs")

    conn = get_db_connection()

    try:
        # Consulta produtos pendentes
        produtos = conn.execute('''
            SELECT * FROM produtos_processados 
            WHERE status IS NULL OR status != 'finalizado'
            ORDER BY data_emissao DESC
        ''').fetchall()

        # Cálculo de totais
        total_produtos = len(produtos)
        valor_total = sum(p['valor_total'] for p in produtos if p['valor_total'] is not None)

        # Listas únicas para filtros
        fornecedores = list(set(p['fornecedor'] for p in produtos if p['fornecedor']))
        numeros_nfe = list(set(p['numero_nfe'] for p in produtos if p['numero_nfe']))

        return render_template('nfe/painel_nfe.html',
                               produtos=produtos,
                               total_produtos=total_produtos,
                               valor_total=valor_total,
                               fornecedores_unicos=fornecedores,
                               numeros_nfe=numeros_nfe
                               )
    finally:
        conn.close()


@nfe_bp.route('/api/painel')
def painel_api():
    """API que retorna os dados para o painel em formato JSON"""
    conn = get_db_connection()
    try:
        produtos = conn.execute('''
            SELECT * FROM produtos_processados 
            WHERE status IS NULL OR status != 'finalizado'
        ''').fetchall()

        # Garantindo valores padrão
        total_produtos = len(produtos)
        valor_total = sum(float(p['valor_total']) for p in produtos if p['valor_total'] is not None)

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
    """Salva as configurações de um produto específico"""
    data = request.get_json()

    # Validação dos campos obrigatórios
    required_fields = ['id', 'qtd_volumes', 'qtd_por_volume', 'tipo_unidade', 'valor_total', 'ipi']
    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': 'Campos obrigatórios faltando'}), 400

    conn = None
    try:
        conn = get_db_connection()

        # Cálculos dos valores
        qtd_real_unidades = data['qtd_volumes'] * data['qtd_por_volume']
        custo_volume = data['valor_total'] / data['qtd_volumes'] if data['qtd_volumes'] > 0 else 0
        custo_unitario = custo_volume / data['qtd_por_volume'] if data['qtd_por_volume'] > 0 else 0
        custo_com_ipi = custo_unitario * (1 + (data['ipi'] / 100))

        # Atualização no banco de dados
        conn.execute('''
            UPDATE produtos_processados SET
                qtd_volumes = ?,
                qtd_por_volume = ?,
                qtd_real_unidades = ?,
                custo_volume = ?,
                custo_unitario = ?,
                custo_com_ipi = ?,
                status = 'salvo',
                unidade_compra = ?
            WHERE codigo = ?
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

        # Atualiza produto
        conn.execute('''
            UPDATE produtos_processados SET
                unidade_compra = ?,
                qtd_por_volume = ?,
                status = 'configurado'
            WHERE codigo = ?
        ''', (data['tipo_unidade'], data['quantidade_por_volume'], data['productId']))

        # Atualiza configuração
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
    """Finaliza o processamento de uma NF-e"""
    data = request.get_json()

    required_fields = ['numero_nfe', 'saved_products']
    if not all(field in data for field in required_fields):
        return jsonify({'status': 'error', 'message': 'Campos obrigatórios faltando'}), 400

    conn = None
    try:
        conn = get_db_connection()

        # Atualiza status dos produtos
        for product_id in data['saved_products']:
            conn.execute('''
                UPDATE produtos_processados SET
                    status = 'finalizado'
                WHERE codigo = ?
            ''', (product_id,))

        # Registra a NF-e como processada
        if data.get('products') and len(data['products']) > 0:
            produto = data['products'][0]
            conn.execute('''
                INSERT OR REPLACE INTO nfe_processadas (
                    numero_nfe, fornecedor, data_emissao,
                    total_nota, caminho_xml, data_importacao
                ) VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                data['numero_nfe'],
                produto.get('fornecedor'),
                produto.get('data_emissao'),
                data.get('total_value', 0),
                produto.get('caminho_xml', ''),
                datetime.now().isoformat()
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