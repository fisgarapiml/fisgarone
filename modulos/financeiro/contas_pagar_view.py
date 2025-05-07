# novo_arquivo: modulos/financeiro/contas_pagar_view.py
from flask import Blueprint, render_template, request, jsonify, current_app
import sqlite3
import json
from datetime import datetime

contas_pagar_bp = Blueprint('contas_pagar', __name__)

def get_db_connection():
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def calcular_status(vencimento, valor_pago):
    hoje = datetime.today().date()
    try:
        dia, mes, ano = map(int, vencimento.split("/"))
        data_vencimento = datetime(ano, mes, dia).date()
    except Exception:
        return "erro"

    if valor_pago and float(valor_pago) > 0:
        return "Pago"
    elif data_vencimento < hoje:
        return "Vencido"
    elif data_vencimento == hoje:
        return "Hoje"
    else:
        return "Pendente"

@contas_pagar_bp.route("/contas-a-pagar")
def contas_a_pagar():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        hoje = datetime.today()
        mes_param_raw = request.args.get("mes", hoje.month)
        ano_param_raw = request.args.get("ano", hoje.year)

        try:
            mes_param = int(mes_param_raw)
            ano_param = int(ano_param_raw)
        except ValueError:
            mes_param = hoje.month
            ano_param = hoje.year

        filtro = request.args.get("filtro", "mes")
        mes_corrente = f"{int(mes_param):02d}/{ano_param}"

        cursor.execute("""
            SELECT 
                substr(vencimento, 1, 2) as dia,
                SUM(CAST(valor AS FLOAT)) as total,
                CASE 
                    WHEN date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now') 
                         AND (valor_pago IS NULL OR valor_pago = 0) THEN 'overdue'
                    WHEN valor_pago > 0 THEN 'paid'
                    ELSE 'pending'
                END as status
            FROM contas_a_pagar
            WHERE substr(vencimento, 4, 7) = ?
            GROUP BY dia, status
            ORDER BY dia
        """, (mes_corrente,))

        daily_data = {}
        for row in cursor.fetchall():
            dia, total, status = row
            total = abs(total) if total else 0.0
            if dia in daily_data:
                daily_data[dia]['total'] += total
                if status == 'overdue' or (status == 'pending' and daily_data[dia]['status'] == 'paid'):
                    daily_data[dia]['status'] = status
            else:
                daily_data[dia] = {'total': total, 'status': status}

        complete_daily_data = {}
        for day in range(1, 32):
            dia_str = f"{day:02d}"
            complete_daily_data[dia_str] = daily_data.get(dia_str, {'total': 0.0, 'status': 'none'})

        def get_sql_result(query, params=()):
            cursor.execute(query, params)
            result = cursor.fetchone()[0]
            return float(result) if result is not None else 0.0

        total_previsto = get_sql_result("""
            SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
            WHERE substr(vencimento, 4, 7) = ?
        """, (mes_corrente,))

        total_pago = get_sql_result("""
            SELECT SUM(CAST(valor_pago AS FLOAT)) FROM contas_a_pagar
            WHERE substr(vencimento, 4, 7) = ?
        """, (mes_corrente,))

        saldo = total_pago + total_previsto

        valor_vencido_total = get_sql_result("""
            SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
            AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now')
        """)

        valor_hoje_total = get_sql_result("""
            SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
            AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) = date('now')
        """)

        query_lancamentos = """
            SELECT codigo, vencimento, categorias, fornecedor, plano_de_contas, valor, valor_pago
            FROM contas_a_pagar
            WHERE 1=1
        """
        params = []

        if filtro == "atrasados":
            titulo_lancamentos = "Contas Vencidas"
            query_lancamentos += """
                AND (valor_pago IS NULL OR valor_pago = 0)
                AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now')
            """
        elif filtro == "hoje":
            titulo_lancamentos = "Contas a Pagar Hoje"
            query_lancamentos += """
                AND (valor_pago IS NULL OR valor_pago = 0)
                AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) = date('now')
            """
        else:
            titulo_lancamentos = f"Lançamentos de {mes_corrente}"
            query_lancamentos += " AND substr(vencimento, 4, 7) = ?"
            params.append(mes_corrente)

        query_lancamentos += " ORDER BY vencimento ASC"
        cursor.execute(query_lancamentos, params)

        lancamentos = []
        for row in cursor.fetchall():
            codigo, vencimento, categoria, fornecedor, plano, valor, valor_pago = row
            status = calcular_status(vencimento, valor_pago)
            lancamentos.append({
                "codigo": codigo,
                "vencimento": vencimento,
                "categoria": categoria or '-',
                "fornecedor": fornecedor or '-',
                "plano": plano or '-',
                "valor": float(valor) if valor is not None else 0.0,
                "pago": float(valor_pago) if valor_pago is not None else 0.0,
                "status": status
            })

        return render_template(
            "contas_a_pagar.html",
            total_previsto=total_previsto,
            total_pago=total_pago,
            saldo=saldo,
            vencidas=valor_vencido_total,
            a_vencer=valor_hoje_total,
            lancamentos=lancamentos,
            titulo_lancamentos=titulo_lancamentos,
            formatar_brl=formatar_brl,
            daily_payments=json.dumps(complete_daily_data),
            current_month=mes_param,
            current_year=ano_param,
            mes_corrente=mes_corrente
        )

    except Exception as e:
        print(f"Erro: {str(e)}")
        return render_template("error.html", error=str(e))
    finally:
        conn.close()
