from flask import Blueprint, render_template, request, jsonify
import sqlite3
from datetime import datetime

config_unidades_bp = Blueprint('config_unidades', __name__, url_prefix='/config-unidades')


def get_db():
    conn = sqlite3.connect('grupo_fisgar.db')
    conn.row_factory = sqlite3.Row
    return conn


@config_unidades_bp.route('/')
def painel_principal():
    """Rota principal que renderiza o painel com dados reais"""
    try:
        conn = get_db()

        # Consulta para produtos pendentes
        pendentes = conn.execute("""
            SELECT DISTINCT
                codigo as codigo_fornecedor,
                descricao as nome,
                unidade as unidade_compra
            FROM produtos_nfe
            WHERE codigo NOT IN (
                SELECT codigo_fornecedor FROM configuracoes_unidades
            )
        """).fetchall()

        # Consulta para produtos configurados
        configurados = conn.execute("""
            SELECT 
                codigo_fornecedor,
                nome,
                unidade_compra,
                qtd_por_volume,
                qtd_por_pacote,
                strftime('%d/%m/%Y %H:%M', atualizado_em) as atualizado_formatado
            FROM configuracoes_unidades
            WHERE ativo = 1
            ORDER BY nome
        """).fetchall()

        # Contagem para os KPIs
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
    """Endpoint para salvar/atualizar configurações"""
    try:
        dados = request.get_json()

        # Validação dos campos obrigatórios
        campos_obrigatorios = ['codigo_fornecedor', 'nome', 'unidade_compra']
        if not all(campo in dados for campo in campos_obrigatorios):
            return jsonify({"status": "error", "message": "Campos obrigatórios faltando"}), 400

        with get_db() as conn:
            cursor = conn.cursor()

            # Verifica se já existe
            cursor.execute("""
                SELECT id FROM configuracoes_unidades
                WHERE codigo_fornecedor = ? AND unidade_compra = ?
            """, (dados['codigo_fornecedor'], dados['unidade_compra']))

            existe = cursor.fetchone()

            if existe:
                # Atualização
                cursor.execute("""
                    UPDATE configuracoes_unidades
                    SET nome = ?,
                        qtd_por_volume = ?,
                        qtd_por_pacote = ?,
                        atualizado_em = datetime('now')
                    WHERE id = ?
                """, (
                    dados['nome'],
                    dados.get('qtd_por_volume', 1),
                    dados.get('qtd_por_pacote', 1),
                    existe['id']
                ))
                acao = 'atualizado'
            else:
                # Inserção
                cursor.execute("""
                    INSERT INTO configuracoes_unidades
                    (codigo_fornecedor, nome, unidade_compra, qtd_por_volume, qtd_por_pacote)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    dados['codigo_fornecedor'],
                    dados['nome'],
                    dados['unidade_compra'],
                    dados.get('qtd_por_volume', 1),
                    dados.get('qtd_por_pacote', 1)
                ))
                acao = 'criado'

            conn.commit()

        return jsonify({
            "status": "success",
            "action": acao,
            "codigo": dados['codigo_fornecedor']
        })

    except Exception as e:
        print(f"ERRO AO SALVAR: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500