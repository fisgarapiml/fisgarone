from flask import Blueprint, jsonify
import sqlite3
from flask import current_app


# Padronize o nome do blueprint com _bp no final
api_estoque_bp = Blueprint('api_estoque_bp', __name__)


@api_estoque_bp.route('/')
def estoque():
    """Endpoint da API para dados de estoque"""
    conn = None
    try:
        conn = sqlite3.connect(app.config['DATABASE'])
        cur = conn.cursor()

        # Consultas ao banco de dados
        total = cur.execute("SELECT SUM(quantidade) FROM produtos_processados").fetchone()[0] or 0
        ok = cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade >= 10").fetchone()[0]
        baixo = \
        cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantity < 10 AND quantity > 0").fetchone()[0]
        crit = cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade = 0").fetchone()[0]

        rows = cur.execute("""
            SELECT codigo, nome, fornecedor, quantidade, data_emissao 
            FROM produtos_processados 
            WHERE quantidade <= 10 
            ORDER BY quantidade ASC
        """).fetchall()

        # Processamento dos dados
        detalhe = [{
            "codigo": r[0],
            "nome": r[1],
            "fornecedor": r[2],
            "estoqueAtual": r[3],
            "ultimaEntrada": r[4]
        } for r in rows]

        return jsonify({
            "totalItens": total,
            "itensOk": ok,
            "itensBaixos": baixo,
            "itensCriticos": crit,
            "itensCriticosList": detalhe,
            "entradasMensais": [],
            "saidasMensais": [],
            "valoresPorCategoria": []
        })

    except Exception as e:
        app.logger.error(f"Erro na API de estoque: {str(e)}")
        return jsonify({"error": "Erro ao processar dados de estoque"}), 500

    finally:
        if conn:
            conn.close()