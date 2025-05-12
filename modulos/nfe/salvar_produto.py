from flask import Blueprint, request, jsonify
import sqlite3
import os
from datetime import datetime
from pathlib import Path

salvar_produto_bp = Blueprint('salvar_produto_bp', __name__, url_prefix='/painel-nfe')

DB_PATH = Path(__file__).resolve().parent.parent.parent / 'grupo_fisgar.db'

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

@salvar_produto_bp.route('/salvar-produto', methods=['POST'])
def salvar_produto():
    try:
        dados = request.get_json(force=True)
        print("🔍 Produto recebido:", dados)

        campos = [
            'codigo_fornecedor', 'nome', 'quantidade', 'valor_total', 'ipi',
            'qtd_volumes', 'qtd_por_volume', 'numero_nfe', 'fornecedor', 'data_emissao'
        ]
        for campo in campos:
            if campo not in dados:
                return jsonify({'status': 'error', 'message': f'Campo ausente: {campo}'}), 400

        qtd_volumes = int(dados['qtd_volumes'])
        qtd_por_volume = int(dados['qtd_por_volume'])
        qtd_real_unidades = qtd_volumes * qtd_por_volume
        custo_volume = float(dados['valor_total']) / qtd_volumes
        custo_unitario = custo_volume / qtd_por_volume
        custo_com_ipi = custo_unitario * (1 + float(dados['ipi']) / 100)

        conn = get_db_connection()
        cur = conn.cursor()

        # Inserir produto no banco
        cur.execute("""
            INSERT INTO produtos_processados (
                codigo_fornecedor, nome, unidade_compra, quantidade, valor_total, ipi,
                qtd_volumes, qtd_por_volume, qtd_real_unidades, custo_volume, custo_unitario,
                custo_com_ipi, fornecedor, numero_nfe, data_emissao, caminho_xml,
                novo, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            dados['codigo_fornecedor'], dados['nome'], dados.get('unidade_compra', 'UN'),
            dados['quantidade'], dados['valor_total'], dados['ipi'],
            qtd_volumes, qtd_por_volume, qtd_real_unidades, custo_volume, custo_unitario,
            custo_com_ipi, dados['fornecedor'], dados['numero_nfe'], dados['data_emissao'],
            dados.get('caminho_xml', ''), '0', 'salvo'
        ))

        conn.commit()
        conn.close()

        print("✅ Produto salvo com sucesso no banco.")

        return jsonify({
            'status': 'success',
            'message': 'Produto salvo com sucesso',
            'custo_unitario': round(custo_unitario, 4),
            'custo_com_ipi': round(custo_com_ipi, 4)
        })

    except Exception as e:
        print("❌ ERRO ao salvar produto:", e)
        return jsonify({'status': 'error', 'message': f'Erro ao salvar produto: {str(e)}'}), 500
