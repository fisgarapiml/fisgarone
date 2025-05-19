from flask import Blueprint, render_template, request, jsonify
from flask import current_app
import sqlite3
from datetime import datetime

produtos_bp = Blueprint('produtos', __name__,
                        template_folder='templates',
                        static_folder='static')

def get_db_connection():
    # Caminho ABSOLUTO pode ser necessário dependendo do deploy!
    conn = sqlite3.connect(current_app.config.get('DATABASE', 'grupo_fisgar.db'))
    conn.row_factory = sqlite3.Row
    return conn

@produtos_bp.route('/')
def index():
    conn = get_db_connection()
    try:
        produtos = conn.execute('''
            SELECT
                codigo,
                codigo_fornecedor,
                nome,
                unidade_compra,
                quantidade,
                valor_total,
                ipi,
                qtd_volumes,
                qtd_por_volume,
                qtd_real_unidades,
                COALESCE(custo_volume, 0) as custo_volume,
                COALESCE(custo_unitario, 0) as custo_unitario,
                COALESCE(custo_com_ipi, 0) as custo_com_ipi,
                fornecedor,
                numero_nfe,
                data_emissao,
                caminho_xml,
                novo,
                status,
                qtd_por_volume_extraida
            FROM produtos_processados
            ORDER BY data_emissao DESC
        ''').fetchall()

        # Caso queira separar categorias depois, precisa de um campo específico para isso
        # categorias = conn.execute('''
        #     SELECT DISTINCT categorias
        #     FROM produtos_processados
        #     WHERE categorias IS NOT NULL
        # ''').fetchall()

        return render_template('produtos.html',
                               produtos=produtos,
                               # categorias=[c['categorias'] for c in categorias] if categorias else []
                               )
    finally:
        conn.close()

@produtos_bp.route('/produtos/obter/<int:codigo>')
def obter_produto(codigo):
    print("DEBUG: Buscando codigo =", codigo)
    conn = get_db_connection()
    produto = conn.execute('SELECT * FROM produtos_processados WHERE codigo = ?', (codigo,)).fetchone()
    print("DEBUG: Resultado do produto:", produto)
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

        qtd_volumes = int(safe_float(dados.get('qtd_volumes'), 1))
        qtd_por_volume = int(safe_float(dados.get('qtd_por_volume'), 1))
        valor_total = safe_float(dados.get('valor_total'))
        ipi = safe_float(dados.get('ipi'))

        custo_volume = valor_total / qtd_volumes if qtd_volumes else 0
        custo_unitario = custo_volume / qtd_por_volume if qtd_por_volume else 0
        custo_com_ipi = custo_unitario * (1 + ipi / 100)
        qtd_real_unidades = qtd_volumes * qtd_por_volume

        cursor.execute('''
            INSERT INTO produtos_processados (
                codigo_fornecedor, nome, unidade_compra, quantidade, valor_total, ipi,
                qtd_volumes, qtd_por_volume, qtd_real_unidades, custo_volume, custo_unitario,
                custo_com_ipi, fornecedor, numero_nfe, data_emissao, caminho_xml, novo, status, qtd_por_volume_extraida
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
            dados.get('novo', ''),
            dados.get('status', 'pendente'),
            dados.get('qtd_por_volume_extraida', None)
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

# ====== ATALHOS DE ROTA ======

# Atalho para aceitar /adicionar-produto além de /produtos/adicionar
@produtos_bp.route('/adicionar-produto', methods=['POST'])
def adicionar_produto_alias():
    return adicionar_produto()

