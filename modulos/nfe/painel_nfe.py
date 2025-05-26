from flask import Blueprint, jsonify, request, current_app, render_template
import os
import sqlite3
from xml.etree import ElementTree as ET
from .processamento_nfe import extrair_dados_xml, salvar_nfe_db, obter_dados_nfe, cadastrar_produtos_nfe
from flask import send_file

from flask import Blueprint, render_template

nfe_bp = Blueprint('nfe_bp', __name__, url_prefix='/nfe')
#           ^^^^^^       ^^^^^^^

@nfe_bp.route('/painel')
def painel():
    return render_template('nfe/painel_nfe.html')

# -------- LISTA OS XMLS DA PASTA -------
@nfe_bp.route('/listar-arquivos', methods=['GET'])
def listar_arquivos():
    pasta_xml = current_app.config['COMPRAS_XML']
    caminho_db = current_app.config['DATABASE']
    arquivos_xml = [f for f in os.listdir(pasta_xml) if f.lower().endswith('.xml')]

    # Chaves já processadas
    conn = sqlite3.connect(caminho_db)
    cursor = conn.cursor()
    cursor.execute("SELECT nfe_chave FROM produtos_nfe")
    chaves_banco = set(row[0] for row in cursor.fetchall())

    lista = []
    for arquivo in arquivos_xml:
        try:
            caminho_xml = os.path.join(pasta_xml, arquivo)
            tree = ET.parse(caminho_xml)
            root = tree.getroot()
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}
            infNFe = root.find('.//nfe:infNFe', ns)
            chave = infNFe.attrib['Id'][3:] if infNFe is not None else ''
            status = 'Processado' if chave in chaves_banco else 'Não processado'
            emit = infNFe.find('nfe:emit', ns) if infNFe is not None else None
            fornecedor = emit.find('nfe:xNome', ns).text if emit is not None else ''
            produtos = infNFe.findall('nfe:det', ns) if infNFe is not None else []
            total_itens = sum(float(p.find('nfe:prod', ns).find('nfe:qCom', ns).text) for p in produtos)
            total = infNFe.find('nfe:total/nfe:ICMSTot', ns) if infNFe is not None else None
            valor_total = float(total.find('nfe:vNF', ns).text) if total is not None else 0
        except Exception as e:
            chave = ''
            status = f'Erro: {str(e)}'
            fornecedor = ''
            total_itens = 0
            valor_total = 0
        lista.append({
            'arquivo': arquivo,
            'chave': chave,
            'status': status,
            'fornecedor': fornecedor,
            'total_itens': total_itens,
            'valor_total': valor_total
        })
    conn.close()
    return jsonify({'status': 'success', 'arquivos': lista})

# -------- VISUALIZA UM XML (JSON COMPLETO) -------
@nfe_bp.route('/visualizar-xml', methods=['GET'])
def visualizar_xml():
    try:
        arquivo = request.args.get('arquivo')
        if not arquivo:
            current_app.logger.error('Nome do arquivo não fornecido')
            return jsonify({'status': 'error', 'message': 'Nome do arquivo não fornecido'}), 400

        pasta_xml = current_app.config['COMPRAS_XML']
        caminho_xml = os.path.join(pasta_xml, arquivo)

        if not os.path.exists(caminho_xml):
            current_app.logger.error(f'Arquivo não encontrado: {caminho_xml}')
            return jsonify({'status': 'error', 'message': 'Arquivo não encontrado'}), 404

        # Extrai dados do XML com tratamento robusto
        try:
            tree = ET.parse(caminho_xml)
            root = tree.getroot()
            ns = {'nfe': 'http://www.portalfiscal.inf.br/nfe'}

            infNFe = root.find('.//nfe:infNFe', ns)
            if infNFe is None:
                raise Exception("Tag infNFe não encontrada no XML")

            # Extração dos dados básicos
            chave = infNFe.attrib.get('Id', '')[3:]  # Remove 'NFe' do início
            emitente = infNFe.find('nfe:emit', ns)
            fornecedor = emitente.find('nfe:xNome', ns).text if emitente is not None else ''
            cnpj_emitente = emitente.find('nfe:CNPJ', ns).text if emitente is not None else ''

            # Data de emissão
            ide = infNFe.find('nfe:ide', ns)
            data_emissao = ide.find('nfe:dhEmi', ns).text if ide is not None else ''

            # Valor total
            total = infNFe.find('nfe:total/nfe:ICMSTot', ns)
            valor_total = float(total.find('nfe:vNF', ns).text) if total is not None else 0.0

            # Produtos
            produtos = []
            for det in infNFe.findall('nfe:det', ns):
                prod = det.find('nfe:prod', ns)
                if prod is not None:
                    produtos.append({
                        'descricao': prod.find('nfe:xProd', ns).text if prod.find('nfe:xProd', ns) is not None else '',
                        'codigo': prod.find('nfe:cProd', ns).text if prod.find('nfe:cProd', ns) is not None else '',
                        'ncm': prod.find('nfe:NCM', ns).text if prod.find('nfe:NCM', ns) is not None else '',
                        'quantidade': float(prod.find('nfe:qCom', ns).text) if prod.find('nfe:qCom',
                                                                                         ns) is not None else 0.0,
                        'unidade': prod.find('nfe:uCom', ns).text if prod.find('nfe:uCom', ns) is not None else 'UN',
                        'valor_unitario': float(prod.find('nfe:vUnCom', ns).text) if prod.find('nfe:vUnCom',
                                                                                               ns) is not None else 0.0,
                        'valor_total': float(prod.find('nfe:vProd', ns).text) if prod.find('nfe:vProd',
                                                                                           ns) is not None else 0.0
                    })

            return jsonify({
                'status': 'success',
                'dados': {
                    'chave': chave,
                    'emitente': {
                        'nome': fornecedor,
                        'cnpj': cnpj_emitente
                    },
                    'data_emissao': data_emissao,
                    'valor_total': valor_total,
                    'produtos': produtos
                }
            })

        except ET.ParseError as e:
            current_app.logger.error(f'Erro ao parsear XML: {str(e)}')
            return jsonify({'status': 'error', 'message': 'Erro ao ler arquivo XML'}), 500
        except Exception as e:
            current_app.logger.error(f'Erro ao processar XML: {str(e)}')
            return jsonify({'status': 'error', 'message': f'Erro ao processar XML: {str(e)}'}), 500

    except Exception as e:
        current_app.logger.error(f'Erro geral: {str(e)}')
        return jsonify({'status': 'error', 'message': 'Erro interno no servidor'}), 500

# -------- SALVAR XML NO BANCO (SÓ OS CAMPOS IMPORTANTES) -------
@nfe_bp.route('/salvar-xml', methods=['POST'])
def salvar_xml():
    try:
        # Validação básica do request
        if not request.is_json:
            return jsonify({'status': 'error', 'message': 'Content-Type deve ser application/json'}), 400

        data = request.get_json()
        arquivo = data.get('arquivo')

        if not arquivo or not isinstance(arquivo, str):
            return jsonify({'status': 'error', 'message': 'Nome do arquivo inválido'}), 400

        pasta_xml = current_app.config['COMPRAS_XML']
        caminho_db = current_app.config['DATABASE']
        caminho_xml = os.path.join(pasta_xml, arquivo)

        # Verifica se arquivo existe
        if not os.path.exists(caminho_xml):
            return jsonify({'status': 'error', 'message': f'Arquivo {arquivo} não encontrado'}), 404

        # Processa produtos editados ou extrai do XML
        produtos = data.get('produtos', [])

        if produtos:
            # Valida estrutura dos produtos editados
            if not isinstance(produtos, list):
                return jsonify({'status': 'error', 'message': 'Formato de produtos inválido'}), 400

            produtos_validos = []
            for idx, prod in enumerate(produtos):
                if not isinstance(prod, dict):
                    return jsonify({
                        'status': 'error',
                        'message': f'Produto na posição {idx} não é um objeto válido'
                    }), 400

                # Filtra apenas campos válidos
                produto_filtrado = {
                    'nfe_chave': prod.get('nfe_chave', ''),
                    'numero': prod.get('numero', ''),
                    'fornecedor': prod.get('fornecedor', ''),
                    'data_emissao': prod.get('data_emissao', ''),
                    'descricao': prod.get('descricao', ''),
                    'codigo': prod.get('codigo', ''),
                    'ncm': prod.get('ncm', ''),
                    'quantidade': float(prod.get('quantidade', 0)),
                    'unidade': prod.get('unidade', ''),
                    'valor_unitario': float(prod.get('valor_unitario', 0)),
                    'valor_total': float(prod.get('valor_total', 0)),
                    'ipi': float(prod.get('ipi', 0)),
                    'st': prod.get('st', ''),
                    'serie': prod.get('serie', ''),
                    'modelo': prod.get('modelo', ''),
                    'cnpj_emitente': prod.get('cnpj_emitente', '')
                }
                produtos_validos.append(produto_filtrado)
        else:
            # Extrai dados do XML se não houver produtos editados
            dados_xml = extrair_dados_xml(caminho_xml)

            if not dados_xml:
                return jsonify({
                    'status': 'error',
                    'message': 'Não foi possível extrair dados do XML'
                }), 400

            # Normaliza estrutura para lista de produtos
            if isinstance(dados_xml, dict):
                produtos_validos = [dados_xml]
            else:
                produtos_validos = dados_xml

        # Converte para lista de dicionários filtrados
        campos_validos = [
            'nfe_chave', 'numero', 'fornecedor', 'data_emissao', 'descricao',
            'codigo', 'ncm', 'quantidade', 'unidade', 'valor_unitario', 'valor_total',
            'ipi', 'st', 'serie', 'modelo', 'cnpj_emitente'
        ]

        produtos_finais = []
        for produto in produtos_validos:
            produto_filtrado = {k: produto.get(k, '') for k in campos_validos}

            # Converte valores numéricos
            for campo in ['quantidade', 'valor_unitario', 'valor_total', 'ipi']:
                try:
                    produto_filtrado[campo] = float(produto_filtrado[campo])
                except (ValueError, TypeError):
                    produto_filtrado[campo] = 0.0

            produtos_finais.append(produto_filtrado)

        # Salva no banco de dados
        resultado = salvar_nfe_db(caminho_db, produtos_finais)

        if not resultado or resultado.get('status') != 'success':
            raise Exception(resultado.get('message', 'Erro desconhecido ao salvar no banco'))

        return jsonify({
            'status': 'success',
            'message': 'NF-e processada com sucesso!',
            'dados': {
                'arquivo': arquivo,
                'produtos_processados': len(produtos_finais)
            }
        })

    except Exception as e:
        current_app.logger.error(f'Erro ao salvar XML: {str(e)}', exc_info=True)
        return jsonify({
            'status': 'error',
            'message': f'Erro ao processar NF-e: {str(e)}'
        }), 500


@nfe_bp.route('/baixar-xml', methods=['GET'])
def baixar_xml():
    arquivo = request.args.get('arquivo')
    if not arquivo:
        return jsonify({'status': 'error', 'message': 'Arquivo não informado'}), 400

    pasta_xml = current_app.config['COMPRAS_XML']
    caminho_xml = os.path.join(pasta_xml, arquivo)

    if not os.path.exists(caminho_xml):
        return jsonify({'status': 'error', 'message': 'Arquivo não encontrado'}), 404

    try:
        return send_file(
            caminho_xml,
            as_attachment=True,
            download_name=arquivo,
            mimetype='application/xml'
        )
    except Exception as e:
        current_app.logger.error(f'Erro ao baixar XML: {str(e)}')
        return jsonify({'status': 'error', 'message': str(e)}), 500