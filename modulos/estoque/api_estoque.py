from flask import Blueprint, jsonify
import sqlite3

api_estoque = Blueprint('api_estoque', __name__)

@api_estoque.route('/api/estoque')
def estoque():
    conn = sqlite3.connect('grupo_fisgar.db')
    cur = conn.cursor()
    total = cur.execute("SELECT SUM(quantidade) FROM produtos_processados").fetchone()[0] or 0
    ok = cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade >= 10").fetchone()[0]
    baixo = cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade < 10 AND quantidade > 0").fetchone()[0]
    crit = cur.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade = 0").fetchone()[0]
    rows = cur.execute("SELECT codigo,nome,fornecedor,quantidade,data_emissao FROM produtos_processados WHERE quantidade <= 10 ORDER BY quantidade ASC").fetchall()
    conn.close()
    detalhe = [{"codigo":r[0],"nome":r[1],"fornecedor":r[2],"estoqueAtual":r[3],"ultimaEntrada":r[4]} for r in rows]
    return jsonify({"totalItens":total,"itensOk":ok,"itensBaixos":baixo,"itensCriticos":crit,"itensCriticosList":detalhe,"entradasMensais":[],"saidasMensais":[],"valoresPorCategoria":[]})