from flask import Blueprint, render_template, request, jsonify
from flask import current_app
import sqlite3
from datetime import datetime

produtos_bp = Blueprint('produtos', __name__,
                        template_folder='templates',
                        static_folder='static')


def get_db_connection():
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


@produtos_bp.route('/produtos')
def index():
    conn = get_db_connection()
    try:
        produtos = conn.execute('''
            SELECT 
                codigo_fornecedor as codigo,
                nome,
                unidade_compra,
                qtd_volumes,
                qtd_por_volume,
                ipi,
                (qtd_volumes * qtd_por_volume) as quantidade_total,
                (custo_volume * qtd_por_volume) as custo_unitario,
                (custo_volume * qtd_por_volume * (1 + ipi/100)) as custo_com_ipi,
                (qtd_volumes * qtd_por_volume * custo_volume * (1 + ipi/100)) as valor_total,
                fornecedor,
                numero_nfe,
                data_emissao,
                status
            FROM produtos
            ORDER BY data_atualizacao DESC
        ''').fetchall()

        categorias = conn.execute('''
            SELECT DISTINCT categorias 
            FROM produtos 
            WHERE categorias IS NOT NULL
        ''').fetchall()

        return render_template('produtos.html',
                               produtos=produtos,
                               categorias=[c['categorias'] for c in categorias])
    finally:
        conn.close()

@produtos_bp.route('/produtos/obter/<int:codigo_fornecedor>')
def obter_produto(codigo_fornecedor):
    conn = get_db_connection()
    produto = conn.execute('SELECT * FROM produtos WHERE codigo_fornecedor = ?', (codigo_fornecedor,)).fetchone()
    conn.close()

    if produto:
        return jsonify({
            'status': 'success',
            'produto': dict(produto)
        })
    return jsonify({'status': 'error', 'message': 'Produto não encontrado'})

@produtos_bp.route('/produtos/adicionar', methods=['POST'])
def adicionar_produto():
    dados = request.get_json()
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Extrair campos com segurança
        qtd_volumes = int(dados.get('qtd_volumes', 1))
        qtd_por_volume = int(dados.get('qtd_por_volume', 1))
        valor_total = float(dados.get('valor_total', 0))
        ipi = float(dados.get('ipi', 0))

        custo_volume = valor_total / qtd_volumes if qtd_volumes else 0
        custo_unitario = custo_volume / qtd_por_volume if qtd_por_volume else 0
        custo_com_ipi = custo_unitario * (1 + ipi / 100)
        qtd_real_unidades = qtd_volumes * qtd_por_volume

        cursor.execute('''
            INSERT INTO produtos (
                codigo_fornecedor, nome, unidade_compra, quantidade, valor_total, ipi,
                qtd_volumes, qtd_por_volume, qtd_real_unidades, custo_volume, custo_unitario,
                custo_com_ipi, fornecedor, numero_nfe, data_emissao, caminho_xml, status, origem, data_cadastro
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            dados.get('codigo_fornecedor'),
            dados.get('nome'),
            dados.get('unidade_compra', 'UN'),
            qtd_real_unidades,
            valor_total,
            ipi,
            qtd_volumes,
            qtd_por_volume,
            qtd_real_unidades,
            custo_volume,
            custo_unitario,
            custo_com_ipi,
            dados.get('fornecedor', ''),
            dados.get('numero_nfe', ''),
            dados.get('data_emissao', ''),
            dados.get('caminho_xml', ''),
            dados.get('status', 'salvo'),
            'manual',
            datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        ))

        conn.commit()
        produto_id = cursor.lastrowid
        conn.close()

        return jsonify({
            'status': 'success',
            'message': 'Produto adicionado com sucesso',
            'produto_id': produto_id
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro ao adicionar produto: {str(e)}'
        })
