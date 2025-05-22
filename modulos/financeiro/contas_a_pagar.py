from flask import Blueprint, render_template, request, jsonify, current_app, make_response, abort
import json
from datetime import datetime, timedelta
import pandas as pd
import re
from weasyprint import HTML
from utils.conexao_postgres import get_db_connection  # Importa sua conexão correta (psycopg2)

contas_a_pagar_bp = Blueprint('contas_a_pagar_bp', __name__)


# ----------------------------
# MAPEAMENTOS
# ----------------------------

mapeamento_categorias = {
    "Café da Manhã": "Alimentação",
    "Reembolsos": "Custo de Vendas",
    "Procuradoria PGFN": "Impostos",
    "Inmetro 40x25": "Insumos",
    "DAS de Parcelamento": "Dívidas Parceladas",
    "Padrão": "Simples Nacional",
    "Sistema Integrador": "Software",
    "Point Chips (Pipoca)": "Fornecedores",
    "Kikakau (Bolibol)": "Fornecedores",
    "Billispel": "Fornecedores",
    "Aluguel": "Fixo",
    "Fatura": "Cartões",
    "Jhan": "Fornecedores",
    "Vale Transporte": "Funcionários",
    "Salário": "Funcionários",
    "bonificação": "Funcionários",
    "FGTS": "Funcionários",
    "Gabriel": "Funcionários",
    "Lara Peçanha": "Funcionários",
    "Jtoys": "Fornecedores",
    "MiniPlay": "Fornecedores",
    "Marsil Atacadista": "Fornecedores",
    "Manos Doces": "Fornecedores",
    "Point Chips": "Fornecedores",
    "Nucita": "Fornecedores",
    "ALFA FULGA COMERCIIO": "Fornecedores",
    "Contabilidade": "Custo Fixo",
    "Altamiris Goes": "Custo Fixo",
    "Simples Nacional": "Impostos",
    "Vale Refeição": "Alimentação",
    "Produtos de Limpeza ou manutenção": "Insumos",
    "Envios Flex": "Custo Entregas",
    "Acordo/Empréstimo": "Dívidas Parceladas",
}

custo_fixo_variavel = {
    "salário": "Fixo",
    "advocacia": "Fixo",
    "vale transporte": "Fixo",
    "água": "Fixo",
    "energia": "Fixo",
    "telefone": "Fixo",
    "vale refeição": "Fixo",
    "fgts": "Fixo",
    "acordo/empréstimo": "Fixo",
    "contabilidade": "Fixo",
    "das de parcelamento": "Fixo",
    "aluguel": "Fixo",
    "impostos": "Variável",
    "insumos": "Variável",
    "custo de vendas": "Variável",
    "software": "Fixo",
    "fornecedores": "Variável",
    "cartões": "Variável",
    "Altamiris Goes": "Fixo",
    "Funcionários": "Fixo",
    "Dívidas Parceladas": "Fixo",
    "Água/Luz/Telefone": "Fixo",
    "Outros": "Variável"
}

mapeamento_colunas = {
    "r__valor": "valor",
    "r__pendente": "valor_pendente",
    "r__pago": "valor_pago",
    "coment_rios": "comentario",
    "c_digo": "codigo_externo",
    "n__documento": "documento",
    "data_compet_ncia": "data_competencia"
}

def normalizar_nome_coluna(nome):
    return re.sub(r'[^a-zA-Z0-9_]', '_', nome)

def carregar_planilha_google_sheets(sheet_id, aba):
    url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={aba}"
    try:
        df = pd.read_csv(url)
        print("✅ Planilha carregada com sucesso do Google Sheets.")
        return df
    except Exception as e:
        print(f"❌ Erro ao carregar a planilha: {e}")
        return None

def processar_dados(df):
    df.columns = [normalizar_nome_coluna(c.lower().strip()) for c in df.columns]
    df.rename(columns=mapeamento_colunas, inplace=True)
    if 'codigo' not in df.columns:
        df['codigo'] = range(1, len(df) + 1)
    if 'plano_de_contas' not in df.columns:
        df['plano_de_contas'] = "Outros"
    df['categorias'] = df['plano_de_contas'].map(mapeamento_categorias).fillna("Outros")
    df['tipo_custo'] = df['categorias'].apply(
        lambda x: "Fixo" if x == "Funcionários" or x == "Custo Fixo" else custo_fixo_variavel.get(x, "Variável")
    )
    for col in ['valor', 'valor_pendente', 'valor_pago']:
        if col in df.columns:
            df[col] = df[col].astype(str).str.replace(",", ".").str.strip()
    if 'valor' in df.columns:
        df['valor'] = df['valor'].astype(float)
        df['valor'] = df['valor'].apply(lambda x: -abs(x))
    df.drop_duplicates(inplace=True)
    print("✅ Dados processados com sucesso.")
    return df


@contas_a_pagar_bp.route("/")
def contas_a_pagar():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        hoje = datetime.today()
        mes_param_raw = request.args.get("mes", hoje.month)
        ano_param_raw = request.args.get("ano", hoje.year)
        dia_param = request.args.get("dia")

        try:
            mes_param = int(mes_param_raw)
            ano_param = int(ano_param_raw)
        except ValueError:
            mes_param = hoje.month
            ano_param = hoje.year

        filtro = request.args.get("filtro", "mes")
        mes_corrente = f"{int(mes_param):02d}/{ano_param}"

        # 1. Query para daily_data (dados por dia)
        cursor.execute("""
            SELECT
                SUBSTRING(vencimento FROM 1 FOR 2) as dia,
                SUM(CAST(valor AS FLOAT)) as total,
                CASE
                    WHEN TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
                         AND (valor_pago IS NULL OR valor_pago = 0) THEN 'overdue'
                    WHEN valor_pago > 0 THEN 'paid'
                    ELSE 'pending'
                END as status
            FROM contas_a_pagar
            WHERE SUBSTRING(vencimento FROM 4 FOR 7) = %s
            GROUP BY SUBSTRING(vencimento FROM 1 FOR 2),
                     CASE
                        WHEN TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
                             AND (valor_pago IS NULL OR valor_pago = 0) THEN 'overdue'
                        WHEN valor_pago > 0 THEN 'paid'
                        ELSE 'pending'
                     END
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
            WHERE SUBSTRING(vencimento FROM 4 FOR 7) = %s
        """, (mes_corrente,))

        total_pago = get_sql_result("""
            SELECT SUM(CAST(valor_pago AS FLOAT)) FROM contas_a_pagar
            WHERE SUBSTRING(vencimento FROM 4 FOR 7) = %s
        """, (mes_corrente,))

        saldo = total_pago + total_previsto

        valor_vencido_total = get_sql_result("""
            SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
            AND TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
        """)

        valor_hoje_total = get_sql_result("""
            SELECT SUM(CAST(valor AS FLOAT)) FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
            AND TO_DATE(vencimento, 'DD/MM/YYYY') = CURRENT_DATE
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
                AND TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
            """
        elif filtro == "hoje":
            titulo_lancamentos = "Contas a Pagar Hoje"
            query_lancamentos += """
                AND (valor_pago IS NULL OR valor_pago = 0)
                AND TO_DATE(vencimento, 'DD/MM/YYYY') = CURRENT_DATE
            """
        else:
            query_lancamentos += " AND SUBSTRING(vencimento FROM 4 FOR 7) = %s"
            params.append(mes_corrente)
            if dia_param:
                query_lancamentos += " AND SUBSTRING(vencimento FROM 1 FOR 2) = %s"
                params.append(f"{int(dia_param):02d}")
                titulo_lancamentos = f"Lançamentos do dia {str(dia_param).zfill(2)}/{mes_corrente[-4:]}"
            else:
                titulo_lancamentos = f"Lançamentos de {mes_corrente}"

        query_lancamentos += " ORDER BY TO_DATE(vencimento, 'DD/MM/YYYY') ASC"
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


@contas_a_pagar_bp.route('/api/contas_por_mes')
def api_contas_por_mes():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT
            SUBSTRING(vencimento FROM 4 FOR 7) as mes_ano,
            SUM(CAST(valor AS FLOAT)) as total_previsto,
            SUM(CAST(COALESCE(valor_pago, 0) AS FLOAT)) as total_pago
        FROM contas_a_pagar
        GROUP BY mes_ano
        ORDER BY SUBSTRING(vencimento FROM 7 FOR 4), SUBSTRING(vencimento FROM 4 FOR 2)
    """)

    dados = [
        {"mes": row[0], "previsto": row[1], "pago": abs(row[2])}
        for row in cursor.fetchall()
    ]
    conn.close()
    return jsonify(dados)


@contas_a_pagar_bp.route('/api/categorias_agrupadas')
def categorias_agrupadas():
    mes = request.args.get("mes")
    ano = request.args.get("ano")

    conn = get_db_connection()
    cursor = conn.cursor()

    if mes and ano:
        mes_corrente = f"{int(mes):02d}/{ano}"
        cursor.execute("""
            SELECT categorias, SUM(ABS(CAST(valor AS FLOAT))) as total
            FROM contas_a_pagar
            WHERE SUBSTRING(vencimento FROM 4 FOR 7) = %s
              AND categorias IS NOT NULL AND TRIM(categorias) != ''
              AND valor IS NOT NULL AND TRIM(valor) != ''
            GROUP BY categorias
            HAVING SUM(ABS(CAST(valor AS FLOAT))) > 0
            ORDER BY total DESC
        """, (mes_corrente,))
    elif ano:
        cursor.execute("""
            SELECT categorias, SUM(ABS(CAST(valor AS FLOAT))) as total
            FROM contas_a_pagar
            WHERE SUBSTRING(vencimento FROM 7 FOR 4) = %s
              AND categorias IS NOT NULL AND TRIM(categorias) != ''
              AND valor IS NOT NULL AND TRIM(valor) != ''
            GROUP BY categorias
            HAVING SUM(ABS(CAST(valor AS FLOAT))) > 0
            ORDER BY total DESC
        """, (ano,))
    else:
        cursor.execute("""
            SELECT categorias, SUM(ABS(CAST(valor AS FLOAT))) as total
            FROM contas_a_pagar
            WHERE categorias IS NOT NULL AND TRIM(categorias) != ''
              AND valor IS NOT NULL AND TRIM(valor) != ''
            GROUP BY categorias
            HAVING SUM(ABS(CAST(valor AS FLOAT))) > 0
            ORDER BY total DESC
        """)

    resultado = [{"categoria": row[0], "total": row[1]} for row in cursor.fetchall()]
    conn.close()
    return jsonify(resultado)



@contas_a_pagar_bp.route('/api/lancamentos_filtrados')
def lancamentos_filtrados():
    tipo = request.args.get("tipo")
    valor = request.args.get("valor")
    mes = request.args.get("mes")
    ano = request.args.get("ano")

    conn = get_db_connection()
    cursor = conn.cursor()

    query = """
            SELECT codigo, vencimento, categorias, fornecedor, plano_de_contas, valor, valor_pago
            FROM contas_a_pagar
            WHERE 1=1
        """
    params = []

    if tipo == 'categoria':
        query += " AND LOWER(categorias) = LOWER(%s)"
        params.append(valor)
        if mes and ano:
            query += " AND SUBSTRING(vencimento FROM 4 FOR 7) = %s"
            params.append(f"{int(mes):02d}/{ano}")

    elif tipo == 'mes':
        query += " AND SUBSTRING(vencimento FROM 4 FOR 7) = %s"
        params.append(valor)

    elif tipo == 'card':
        if valor == 'paid':
            query += " AND valor_pago > 0"
        elif valor == 'balance':
            query += " AND (valor_pago IS NULL OR valor_pago = 0)"
        elif valor == 'overdue':
            query += """
                    AND (valor_pago IS NULL OR valor_pago = 0)
                    AND TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
                """
        elif valor == 'today':
            query += """
                    AND (valor_pago IS NULL OR valor_pago = 0)
                    AND TO_DATE(vencimento, 'DD/MM/YYYY') = CURRENT_DATE
                """
        elif valor == 'all':
            pass  # mostra tudo

        if mes and ano:
            query += " AND SUBSTRING(vencimento FROM 4 FOR 7) = %s"
            params.append(f"{int(mes):02d}/{ano}")

    elif tipo == 'dia':
        dia_valor = valor.split('/')[0].zfill(2)
        mes_valor = valor.split('/')[1]
        ano_valor = valor.split('/')[2]
        query += " AND SUBSTRING(vencimento FROM 1 FOR 2) = %s AND SUBSTRING(vencimento FROM 4 FOR 2) = %s AND SUBSTRING(vencimento FROM 7 FOR 4) = %s"
        params.extend([dia_valor, mes_valor, ano_valor])

    query += " ORDER BY TO_DATE(vencimento, 'DD/MM/YYYY') ASC"
    cursor.execute(query, params)

    resultado = [{
        "codigo": row[0],
        "vencimento": row[1],
        "categoria": row[2] or '-',
        "fornecedor": row[3] or '-',
        "plano": row[4] or '-',
        "valor": float(row[5]) if row[5] else 0.0,
        "status": calcular_status(row[1], row[6])
    } for row in cursor.fetchall()]

    conn.close()
    return jsonify(resultado)



@contas_a_pagar_bp.route('/pdf')
def gerar_pdf_contas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        filtro = request.args.get('filtro', 'dia')
        mes = request.args.get('mes', datetime.today().month)
        ano = request.args.get('ano', datetime.today().year)
        hoje = datetime.today().date()
        titulo_param = request.args.get('titulo')
        titulo = "CONTAS A PAGAR"

        query = """
                SELECT vencimento, fornecedor, categorias, plano_de_contas,
                       valor, valor_pago, codigo
                FROM contas_a_pagar
                WHERE (valor_pago IS NULL OR valor_pago = 0)
            """
        params = []

        # Ajuste de filtros para Postgres (substr -> substring, date parsing diferente)
        if filtro == "dia" or filtro == "today":
            titulo = "CONTAS DO DIA" if filtro == "dia" else "CONTAS A PAGAR HOJE"
            query += """
                AND TO_DATE(vencimento, 'DD/MM/YYYY') = CURRENT_DATE
            """
        elif filtro == "atrasados":
            titulo = "CONTAS ATRASADAS"
            query += """
                AND TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
            """
        elif filtro == "segunda":
            titulo = "CONTAS SEGUNDA + FIM DE SEMANA"
            if hoje.weekday() == 0:
                sabado = hoje - timedelta(days=2)
                domingo = hoje - timedelta(days=1)
                segunda = hoje
            else:
                dias_para_segunda = (0 - hoje.weekday()) % 7
                segunda = hoje + timedelta(days=dias_para_segunda)
                sabado = segunda - timedelta(days=2)
                domingo = segunda - timedelta(days=1)
            query += """
                AND (
                    TO_DATE(vencimento, 'DD/MM/YYYY') = %s
                    OR TO_DATE(vencimento, 'DD/MM/YYYY') = %s
                    OR TO_DATE(vencimento, 'DD/MM/YYYY') = %s
                )
            """
            params.extend([
                segunda.strftime('%Y-%m-%d'),
                sabado.strftime('%Y-%m-%d'),
                domingo.strftime('%Y-%m-%d')
            ])
        elif filtro == "all":
            titulo = "TODAS AS CONTAS A PAGAR"
            query = """
                SELECT vencimento, fornecedor, categorias, plano_de_contas,
                       valor, valor_pago, codigo
                FROM contas_a_pagar
            """
        elif filtro == "paid":
            titulo = "CONTAS PAGAS"
            query = """
                SELECT vencimento, fornecedor, categorias, plano_de_contas,
                       valor, valor_pago, codigo
                FROM contas_a_pagar
                WHERE valor_pago > 0
            """
        elif filtro == "balance":
            titulo = "CONTAS EM ABERTO"
            query += """
                AND (valor_pago IS NULL OR valor_pago = 0)
            """
        elif filtro == "mes":
            titulo = f"CONTAS DE {request.args.get('valor', '')}"
            query += " AND SUBSTRING(vencimento FROM 4 FOR 7) = %s"
            params.append(request.args.get('valor'))
        elif filtro == "categoria":
            titulo = f"CONTAS DA CATEGORIA {request.args.get('valor', '').upper()}"
            query += " AND LOWER(categorias) = LOWER(%s)"
            params.append(request.args.get('valor'))

        cursor.execute(query, params)

        lancamentos = []
        for row in cursor.fetchall():
            # psycopg2 retorna tupla, precisa acessar por índice
            lancamentos.append({
                "vencimento": row[0],
                "fornecedor": row[1] or '-',
                "categoria": row[2] or '-',
                "plano": row[3] or '-',
                "valor": float(row[4]) if row[4] else 0.0,
                "pago": float(row[5]) if row[5] else 0.0,
                "status": calcular_status(row[0], row[5])
            })

        if titulo_param:
            titulo = titulo_param

        html = render_template(
            "contas_pdf.html",
            lancamentos=lancamentos,
            titulo=titulo,
            data_emissao=datetime.now().strftime("%d/%m/%Y %H:%M"),
            total_geral=sum(abs(item['valor']) for item in lancamentos)
        )

        pdf = HTML(string=html).write_pdf()

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=contas_a_pagar_{filtro}.pdf'
        return response

    except Exception as e:
        current_app.logger.error(f"Erro ao gerar PDF: {str(e)}")
        abort(500, description="Erro ao gerar relatório PDF")
    finally:
        conn.close()


@contas_a_pagar_bp.route('/editar_lancamento', methods=['POST'])
def editar_lancamento():
    # Recebe JSON ou form-data
    dados = request.get_json() or request.form.to_dict()
    codigo = dados.pop('codigo', None)
    if not codigo:
        return jsonify(success=False, error='Código não fornecido'), 400

    # Monta dinamicamente a parte SET do UPDATE com %s para psycopg2
    campos = [f"{campo} = %s" for campo in dados.keys()]
    valores = list(dados.values())
    valores.append(codigo)

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    f"UPDATE contas_a_pagar SET {', '.join(campos)} WHERE codigo = %s",
                    valores
                )
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()


@contas_a_pagar_bp.route('/marcar_pago', methods=['POST'])
def marcar_pago():
    codigo = request.args.get('codigo')
    if not codigo:
        return jsonify(success=False, error='Código não fornecido'), 400

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE contas_a_pagar SET valor_pago = valor WHERE codigo = %s",
                    (codigo,)
                )
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()



@contas_a_pagar_bp.route('/excluir', methods=['POST'])
def excluir_lancamento():
    codigo = request.args.get('codigo')
    if not codigo:
        return jsonify(success=False, error='Código não fornecido'), 400

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM contas_a_pagar WHERE codigo = %s",
                    (codigo,)
                )
        return jsonify(success=True)
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()


@contas_a_pagar_bp.route('/api/daily_timeline')
def api_daily_timeline():
    mes = request.args.get('mes')
    ano = request.args.get('ano')

    if not mes or not ano:
        return jsonify({"error": "Parâmetros 'mes' e 'ano' são obrigatórios"}), 400

    conn = get_db_connection()
    try:
        with conn:
            with conn.cursor() as cursor:
                # Consulta corrigida - extrai apenas o dia para agrupamento
                cursor.execute("""
                    SELECT
                        SUBSTRING(vencimento FROM 1 FOR 2) as day,
                        SUM(CAST(valor AS FLOAT)) as total,
                        CASE
                            WHEN TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
                                 AND (valor_pago IS NULL OR valor_pago = 0) THEN 'overdue'
                            WHEN valor_pago > 0 THEN 'paid'
                            ELSE 'pending'
                        END as status
                    FROM contas_a_pagar
                    WHERE SUBSTRING(vencimento FROM 4 FOR 2) = %s
                      AND SUBSTRING(vencimento FROM 7 FOR 4) = %s
                    GROUP BY 
                        SUBSTRING(vencimento FROM 1 FOR 2),
                        CASE
                            WHEN TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
                                 AND (valor_pago IS NULL OR valor_pago = 0) THEN 'overdue'
                            WHEN valor_pago > 0 THEN 'paid'
                            ELSE 'pending'
                        END
                    ORDER BY day
                """, (f"{int(mes):02d}", ano))

                # Processa os resultados para consolidar por dia
                daily_data = {}
                for row in cursor.fetchall():
                    day, total, status = row
                    total = abs(total) if total else 0.0
                    if day in daily_data:
                        daily_data[day]['total'] += total
                        # Mantém o status mais crítico (overdue > pending > paid)
                        if status == 'overdue' or (status == 'pending' and daily_data[day]['status'] == 'paid'):
                            daily_data[day]['status'] = status
                    else:
                        daily_data[day] = {'total': total, 'status': status}

                # Preenche todos os dias do mês, mesmo sem lançamentos
                complete_daily_data = {}
                days_in_month = 31  # Máximo de dias em qualquer mês
                for day in range(1, days_in_month + 1):
                    day_str = f"{day:02d}"
                    complete_daily_data[day_str] = daily_data.get(day_str, {'total': 0.0, 'status': 'none'})

        return jsonify(complete_daily_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        conn.close()