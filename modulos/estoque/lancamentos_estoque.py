import sqlite3
from flask import Blueprint, render_template, request, jsonify, send_file
import io
import csv
from datetime import datetime
import os

# Ajuste do template_folder para ser robusto independente da posição do .py
TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../templates/estoque')

lancamentos_estoque_bp = Blueprint(
    'lancamentos_estoque', __name__,
    template_folder=TEMPLATE_DIR
)

def get_db_connection():
    conn = sqlite3.connect('grupo_fisgar.db')
    conn.row_factory = sqlite3.Row
    return conn

@lancamentos_estoque_bp.route('/estoque-lancamentos')
def tela_lancamentos_estoque():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        estoque = cursor.execute("SELECT * FROM estoque").fetchall()
        # Indicadores para cards - blindados
        total_itens = len(estoque) if estoque else 0
        total_estoque = sum((row['preco_custo_total'] or 0) for row in estoque) if estoque else 0.0
        estoque_baixo = sum(1 for row in estoque if (row['qtd_estoque'] or 0) < (row['estoque_minimo'] or 0)) if estoque else 0
        produtos_inativos = sum(1 for row in estoque if (row['status'] or '').lower() == 'inativo') if estoque else 0
        fornecedores_unicos = sorted(set(row['fornecedor_padrao'] for row in estoque if row['fornecedor_padrao'])) if estoque else []
        conn.close()
        return render_template(
            'estoque/interface.html',
            total_itens=total_itens or 0,
            total_estoque=total_estoque or 0.0,
            estoque_baixo=estoque_baixo or 0,
            produtos_inativos=produtos_inativos or 0,
            fornecedores_unicos=fornecedores_unicos or []
        )
    except Exception as e:
        # Log completo para debug em produção
        print(f"Erro na interface: {e}")
        return "Erro ao carregar interface do estoque.", 500

# API: retornar lançamentos (JSON para Tabulator)
@lancamentos_estoque_bp.route('/estoque/api/lancamentos')
def api_lancamentos_estoque():
    conn = get_db_connection()
    estoque = conn.execute("SELECT * FROM estoque").fetchall()
    data = [dict(row) for row in estoque] if estoque else []
    conn.close()
    return jsonify(data)

# API: editar campo ou salvar alteração (inline ou modal)
@lancamentos_estoque_bp.route('/estoque/api/lancamentos/editar', methods=['POST'])
def api_editar_lancamento():
    dados = request.json
    id = dados.get('id')
    # Determina campos válidos
    campos_permitidos = [
        "sku", "codigo", "nome", "imagem", "unidade", "qtd_estoque",
        "estoque_reservado", "estoque_minimo", "estoque_maximo", "localizacao",
        "custo_unitario", "preco_venda", "status", "tipo_produto", "ncm",
        "fornecedor_padrao", "codigo_barras", "percentual_ipi", "preco_custo_total"
    ]
    sets = []
    params = []
    for campo in campos_permitidos:
        if campo in dados and campo != "id":
            sets.append(f"{campo} = ?")
            params.append(dados[campo])
    if not sets:
        return jsonify({"sucesso": False, "erro": "Nada para atualizar"})
    params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    params.append(id)
    conn = get_db_connection()
    conn.execute(f"UPDATE estoque SET {', '.join(sets)}, data_atualizacao = ? WHERE id = ?", params)
    conn.commit()
    conn.close()
    return jsonify({"sucesso": True})

# API: remover lançamento
@lancamentos_estoque_bp.route('/estoque/api/lancamentos/remover', methods=['POST'])
def api_remover_lancamento():
    dados = request.json
    id = dados.get('id')
    conn = get_db_connection()
    conn.execute("DELETE FROM estoque WHERE id = ?", (id,))
    conn.commit()
    conn.close()
    return jsonify({"sucesso": True})

# EXPORTAÇÃO BACKEND: CSV direto do banco
@lancamentos_estoque_bp.route('/estoque/lancamentos/exportar')
def exportar_lancamentos_estoque():
    conn = get_db_connection()
    estoque = conn.execute("SELECT * FROM estoque").fetchall()
    if not estoque:
        conn.close()
        return "Nada para exportar", 204
    fieldnames = estoque[0].keys()
    si = io.StringIO()
    writer = csv.DictWriter(si, fieldnames=fieldnames)
    writer.writeheader()
    for row in estoque:
        writer.writerow(dict(row))
    output = io.BytesIO()
    output.write(si.getvalue().encode('utf-8'))
    output.seek(0)
    conn.close()
    filename = f"estoque_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    return send_file(output, mimetype='text/csv', as_attachment=True, download_name=filename)
