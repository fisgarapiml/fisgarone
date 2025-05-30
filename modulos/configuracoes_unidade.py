from flask import Blueprint, render_template, request, jsonify
import sqlite3
from datetime import datetime

config_unidades_bp = Blueprint('config_unidades', __name__, url_prefix='/config-unidades')

DB = 'grupo_fisgar.db'

def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def garantir_colunas_extra():
    # Garante as colunas calculadas (NÃO APAGA DADO, só adiciona se faltar)
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(configuracoes_unidades)")
        colunas = [row['name'] for row in cursor.fetchall()]
        if 'qtd_total_volume' not in colunas:
            cursor.execute("ALTER TABLE configuracoes_unidades ADD COLUMN qtd_total_volume INTEGER DEFAULT 0")
        if 'quantidade_xml' not in colunas:
            cursor.execute("ALTER TABLE configuracoes_unidades ADD COLUMN quantidade_xml INTEGER DEFAULT 0")
        if 'total_calculado' not in colunas:
            cursor.execute("ALTER TABLE configuracoes_unidades ADD COLUMN total_calculado INTEGER DEFAULT 0")
        if 'custo_unitario_real' not in colunas:
            cursor.execute("ALTER TABLE configuracoes_unidades ADD COLUMN custo_unitario_real REAL DEFAULT 0")
        conn.commit()

def buscar_quantidade_xml(codigo_produto, unidade_compra):
    # Busca quantidade total desse código + unidade nos produtos_nfe
    with get_db() as conn:
        row = conn.execute("""
            SELECT SUM(quantidade) as total
            FROM produtos_nfe
            WHERE codigo = ? AND unidade = ?
        """, (codigo_produto, unidade_compra)).fetchone()
        return int(row['total']) if row and row['total'] else 0

@config_unidades_bp.route('/')
def painel_principal():
    garantir_colunas_extra()
    try:
        conn = get_db()

        # Produtos pendentes (ainda não cadastrados na configuração)
        pendentes = conn.execute("""
            SELECT DISTINCT
                codigo as codigo_fornecedor,
                descricao as nome,
                unidade as unidade_compra
            FROM produtos_nfe
            WHERE (codigo, unidade) NOT IN (
                SELECT codigo_fornecedor, unidade_compra FROM configuracoes_unidades
            )
        """).fetchall()

        # Produtos configurados
        configurados = conn.execute("""
            SELECT 
                codigo_fornecedor,
                nome,
                unidade_compra,
                qtd_por_volume,
                qtd_por_pacote,
                qtd_total_volume,
                quantidade_xml,
                total_calculado,
                valor_total,
                custo_unitario_real,
                strftime('%d/%m/%Y %H:%M', atualizado_em) as atualizado_formatado
            FROM configuracoes_unidades
            WHERE ativo = 1
            ORDER BY nome
        """).fetchall()

        total_pendentes = len(pendentes)
        total_configurados = len(configurados)
        total_itens = total_pendentes + total_configurados

        conn.close()

        return render_template('config_unidades.html',
                               pendentes=pendentes,
                               configurados=configurados,
                               total_pendentes=total_pendentes,
                               total_configurados=total_configurados,
                               total_itens=total_itens,
                               ultima_atualizacao=datetime.now().strftime("%d/%m/%Y %H:%M"))

    except Exception as e:
        print(f"ERRO: {str(e)}")
        return render_template('erro.html', mensagem="Erro ao carregar dados do sistema"), 500

@config_unidades_bp.route('/api/salvar', methods=['POST'])
def salvar_config():
    try:
        dados = request.get_json()
        codigo = dados['codigo_fornecedor']
        nome = dados['nome']
        unidade = dados['unidade_compra']
        qtd_por_volume = int(dados.get('qtd_por_volume', 1))
        qtd_por_pacote = int(dados.get('qtd_por_pacote', 1))
        qtd_total_volume = qtd_por_volume * qtd_por_pacote

        with get_db() as conn:
            cur = conn.cursor()

            # Busca apenas a última NFe para este código + unidade
            cur.execute("""
                SELECT valor_total, quantidade
                FROM produtos_nfe
                WHERE codigo = ? AND unidade = ?
                ORDER BY data_emissao DESC, id DESC
                LIMIT 1
            """, (codigo, unidade))
            ultima = cur.fetchone()
            if ultima and ultima[1]:
                valor_total = round(ultima[0], 3)
                quantidade_xml = ultima[1]
                total_calculado = qtd_total_volume * quantidade_xml
                custo_unitario_real = round(valor_total / total_calculado, 3) if total_calculado else 0
            else:
                valor_total = 0
                quantidade_xml = 0
                total_calculado = 0
                custo_unitario_real = 0

            # Verifica se já existe pelo par código + unidade
            cur.execute("""
                SELECT id FROM configuracoes_unidades
                WHERE codigo_fornecedor = ? AND unidade_compra = ?
            """, (codigo, unidade))
            existe = cur.fetchone()

            if existe:
                cur.execute("""
                    UPDATE configuracoes_unidades
                    SET nome = ?,
                        qtd_por_volume = ?,
                        qtd_por_pacote = ?,
                        qtd_total_volume = ?,
                        quantidade_xml = ?,
                        total_calculado = ?,
                        valor_total = ?,
                        custo_unitario_real = ?,
                        atualizado_em = datetime('now')
                    WHERE id = ?
                """, (
                    nome,
                    qtd_por_volume,
                    qtd_por_pacote,
                    qtd_total_volume,
                    quantidade_xml,
                    total_calculado,
                    valor_total,
                    custo_unitario_real,
                    existe['id']
                ))
                acao = 'atualizado'
            else:
                cur.execute("""
                    INSERT INTO configuracoes_unidades
                    (codigo_fornecedor, nome, unidade_compra, qtd_por_volume, qtd_por_pacote,
                    qtd_total_volume, quantidade_xml, total_calculado, valor_total, custo_unitario_real)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    codigo,
                    nome,
                    unidade,
                    qtd_por_volume,
                    qtd_por_pacote,
                    qtd_total_volume,
                    quantidade_xml,
                    total_calculado,
                    valor_total,
                    custo_unitario_real
                ))
                acao = 'criado'
            conn.commit()

        return jsonify({
            "status": "success",
            "action": acao,
            "codigo": codigo,
            "qtd_total_volume": qtd_total_volume,
            "quantidade_xml": quantidade_xml,
            "total_calculado": total_calculado,
            "valor_total": valor_total,
            "custo_unitario_real": custo_unitario_real
        })

    except Exception as e:
        print(f"ERRO AO SALVAR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

@config_unidades_bp.route('/recalcular-todos', methods=['POST', 'OPTIONS'])
def handle_recalcular():
    if request.method == 'OPTIONS':
        response = jsonify({"status": "preflight"})
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        return response

    print("Endpoint /recalcular-todos acessado via POST")
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, codigo_fornecedor, unidade_compra, qtd_por_volume, qtd_por_pacote FROM configuracoes_unidades")
            for row in cursor.fetchall():
                quantidade_xml = buscar_quantidade_xml(row['codigo_fornecedor'], row['unidade_compra'])
                qtd_total_volume = (row['qtd_por_volume'] or 1) * (row['qtd_por_pacote'] or 1)
                total_calculado = quantidade_xml * qtd_total_volume

                # Busca última NFe para atualizar valor_total e custo_unitario_real
                cursor.execute("""
                    SELECT valor_total, quantidade
                    FROM produtos_nfe
                    WHERE codigo = ? AND unidade = ?
                    ORDER BY data_emissao DESC, id DESC
                    LIMIT 1
                """, (row['codigo_fornecedor'], row['unidade_compra']))
                ultima = cursor.fetchone()
                valor_total = round(ultima[0], 3) if ultima and ultima[0] else 0
                custo_unitario_real = round(valor_total / total_calculado, 3) if total_calculado else 0

                cursor.execute("""
                    UPDATE configuracoes_unidades SET
                        quantidade_xml = ?,
                        qtd_total_volume = ?,
                        total_calculado = ?,
                        valor_total = ?,
                        custo_unitario_real = ?,
                        atualizado_em = datetime('now')
                    WHERE id = ?
                """, (
                    quantidade_xml,
                    qtd_total_volume,
                    total_calculado,
                    valor_total,
                    custo_unitario_real,
                    row['id']
                ))
            conn.commit()

        return jsonify({
            "status": "success",
            "message": "Recálculo completo",
            "updated": datetime.now().isoformat()
        })
    except Exception as e:
        print(f"ERRO CRÍTICO: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500
