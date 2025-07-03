from flask import Blueprint, render_template, request, jsonify
import sqlite3
import os

parametros_bp = Blueprint('parametros_bp', __name__, template_folder='templates')

DB_PATH = os.path.join(os.path.dirname(__file__), '..', '..', 'fisgarone.db')

def db_conn():
    return sqlite3.connect(DB_PATH)

@parametros_bp.route('/financeiro/parametros')
def tela_parametros():
    return render_template('financeiro/parametros.html')

# --------- APIs CRUD (GENÉRICAS PARA TABELAS) ----------

def crud_api(table, fields):
    if request.method == 'GET':
        with db_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"SELECT * FROM {table}")
            dados = [dict(zip([column[0] for column in cur.description], row)) for row in cur.fetchall()]
            return jsonify(dados)

    elif request.method == 'POST':
        dados = request.json
        # Exclui o campo 'id' do insert (NUNCA insira autoincrement no insert!)
        insert_fields = [f for f in fields if f != 'id']
        keys = ','.join(insert_fields)
        vals = ','.join(['?']*len(insert_fields))
        values = [dados.get(f, '') for f in insert_fields]
        with db_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"INSERT INTO {table} ({keys}) VALUES ({vals})", values)
            conn.commit()
            dados['id'] = cur.lastrowid  # Pega o novo ID criado
            return jsonify(dados)

    elif request.method == 'PUT':
        dados = request.json
        pk = dados.get('id')
        setstr = ','.join([f"{f}=?" for f in fields if f != 'id'])
        values = [dados[f] for f in fields if f != 'id']
        values.append(pk)
        with db_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"UPDATE {table} SET {setstr} WHERE id=?", values)
            conn.commit()
            return jsonify(success=True)

    elif request.method == 'DELETE':
        pk = request.args.get('id')
        with db_conn() as conn:
            cur = conn.cursor()
            cur.execute(f"DELETE FROM {table} WHERE id=?", (pk,))
            conn.commit()
            return jsonify(success=True)


@parametros_bp.route('/api/categorias', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_categorias():
    return crud_api('categorias', ['id', 'nome', 'descricao'])

@parametros_bp.route('/api/fornecedores', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_fornecedores():
    return crud_api('fornecedores', ['id', 'nome', 'cnpj', 'email', 'telefone'])

@parametros_bp.route('/api/centro_de_custo', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_centro_de_custo():
    return crud_api('centro_de_custo', ['id', 'nome', 'descricao'])

@parametros_bp.route('/api/contas_bancarias', methods=['GET', 'POST', 'PUT', 'DELETE'])
def api_contas_bancarias():
    return crud_api('contas_bancarias', ['id', 'banco', 'agencia', 'conta', 'titular', 'tipo_conta'])
@parametros_bp.route('/api/sugestoes/<campo>')
def sugestoes_campo(campo):
    validos = {
        'fornecedor': 'fornecedor',
        'categorias': 'categorias',
        'centro_de_custo': 'centro_de_custo',
        'plano_de_contas': 'plano_de_contas',
        'banco_pagamento': 'banco_pagamento'
    }
    if campo not in validos:
        return jsonify([])
    with db_conn() as conn:
        cur = conn.cursor()
        cur.execute(f"SELECT DISTINCT {validos[campo]} FROM contas_a_pagar WHERE {validos[campo]} IS NOT NULL AND {validos[campo]} != ''")
        sugestoes = sorted(set(x[0].strip() for x in cur.fetchall() if x[0]))
        return jsonify(sugestoes)


