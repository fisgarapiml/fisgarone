from flask import Blueprint, render_template, request, jsonify, current_app, make_response, abort
import json
from datetime import datetime, timedelta
import pandas as pd
import re
from weasyprint import HTML
from utils.conexao_postgres import get_db_connection  # Importa sua conexão correta (psycopg2)
import psycopg2.extras


contas_a_pagar_bp = Blueprint('contas_a_pagar_bp', __name__)

# ----------------------------
# MAPEAMENTOS
# ----------------------------

mapeamento_categorias = {
    "Café da Manhã": "Alimentação",
    "Reembolsos": "Custo de vendas",
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

def formatar_brl(valor):
    """Formata o valor para o padrão BRL: R$ 1.234,56"""
    try:
        return f"R$ {float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ 0,00"

def calcular_status(vencimento, valor_pago):
    """Retorna o status do lançamento ('Pago', 'Vencido', 'Hoje', 'Pendente')"""
    hoje = datetime.today().date()
    try:
        dia, mes, ano = map(int, vencimento.split("/"))
        data_vencimento = datetime(ano, mes, dia).date()
    except Exception:
        return "erro"

    try:
        valor_pago_float = float(valor_pago) if valor_pago is not None else 0.0
    except Exception:
        valor_pago_float = 0.0

    if valor_pago_float > 0:
        return "Pago"
    elif data_vencimento < hoje:
        return "Vencido"
    elif data_vencimento == hoje:
        return "Hoje"
    else:
        return "Pendente"


@contas_a_pagar_bp.route("/")
def contas_a_pagar():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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

        # Query para daily_data (dados por dia)
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
            # row pode ser dict ou tuple dependendo do driver, mas usando RealDictCursor é dict!
            dia = row.get("dia") if isinstance(row, dict) else row[0]
            total = row.get("total") if isinstance(row, dict) else row[1]
            status = row.get("status") if isinstance(row, dict) else row[2]
            try:
                total = abs(float(total)) if total is not None else 0.0
            except Exception:
                total = 0.0
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
            result = cursor.fetchone()
            if result is None:
                return 0.0
            if isinstance(result, dict):
                value = list(result.values())[0]
            else:
                value = result[0]
            try:
                return float(value) if value is not None else 0.0
            except Exception:
                return 0.0

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
            codigo = row.get("codigo") if isinstance(row, dict) else row[0]
            vencimento = row.get("vencimento") if isinstance(row, dict) else row[1]
            categoria = row.get("categorias") if isinstance(row, dict) else row[2]
            fornecedor = row.get("fornecedor") if isinstance(row, dict) else row[3]
            plano = row.get("plano_de_contas") if isinstance(row, dict) else row[4]
            valor = row.get("valor") if isinstance(row, dict) else row[5]
            valor_pago = row.get("valor_pago") if isinstance(row, dict) else row[6]
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
        if conn:
            conn.close()


@contas_a_pagar_bp.route('/api/lancamentos_filtrados')
def lancamentos_filtrados():
    conn = None
    try:
        tipo = request.args.get("tipo")
        valor = request.args.get("valor")
        mes = request.args.get("mes")
        ano = request.args.get("ano")

        if not tipo:
            return jsonify({"error": "Parâmetro 'tipo' é obrigatório"}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        query = """
            SELECT codigo, vencimento, categorias, fornecedor, plano_de_contas, 
                   valor, valor_pago
            FROM contas_a_pagar
            WHERE 1=1
        """
        params = []

        # Construção dos filtros
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

            if mes and ano:
                query += " AND SUBSTRING(vencimento FROM 4 FOR 7) = %s"
                params.append(f"{int(mes):02d}/{ano}")

        query += " ORDER BY TO_DATE(vencimento, 'DD/MM/YYYY') ASC"
        cursor.execute(query, params)

        # Processamento seguro dos resultados
        lancamentos = []
        for row in cursor.fetchall():
            try:
                valor = row[5] if row[5] is not None else 0.0
                pago = row[6] if row[6] is not None else 0.0

                # Garante que os valores numéricos não sejam NaN
                valor_float = float(valor) if str(valor).strip() else 0.0
                pago_float = float(pago) if str(pago).strip() else 0.0

                lancamentos.append({
                    "codigo": row[0],
                    "vencimento": row[1] or '-',
                    "categoria": row[2] or '-',
                    "fornecedor": row[3] or '-',
                    "plano": row[4] or '-',
                    "valor": abs(valor_float),
                    "pago": abs(pago_float),
                    "status": calcular_status(row[1], row[6])
                })
            except (TypeError, ValueError) as e:
                current_app.logger.warning(f"Registro inválido ignorado: {row} - {str(e)}")
                continue

        return jsonify(lancamentos)

    except Exception as e:
        current_app.logger.error(f"Erro em lancamentos_filtrados: {str(e)}")
        return jsonify({
            "error": "Erro ao filtrar lançamentos",
            "details": str(e)
        }), 500
    finally:
        if conn:
            conn.close()

@contas_a_pagar_bp.route('/api/contas_por_mes')
def api_contas_por_mes():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta corrigida - usando a expressão diretamente no ORDER BY
        query = """
            SELECT 
                SUBSTRING(vencimento FROM 4 FOR 7) as mes_ano,
                COALESCE(SUM(valor::float), 0) as total_previsto,
                COALESCE(SUM(ABS(valor_pago::float)), 0) as total_pago
            FROM contas_a_pagar
            WHERE valor IS NOT NULL
            GROUP BY SUBSTRING(vencimento FROM 4 FOR 7)
            ORDER BY TO_DATE(SUBSTRING(vencimento FROM 4 FOR 7), 'MM/YYYY')
        """

        cursor.execute(query)
        resultados = cursor.fetchall()

        dados = []
        for row in resultados:
            try:
                dados.append({
                    "mes": row[0] if row[0] else '00/0000',
                    "previsto": abs(float(row[1])) if row[1] is not None else 0.0,
                    "pago": abs(float(row[2])) if row[2] is not None else 0.0
                })
            except (TypeError, ValueError) as e:
                current_app.logger.warning(f"Registro inválido ignorado: {row} - {str(e)}")
                continue

        return jsonify(dados)

    except Exception as e:
        current_app.logger.error(f"Erro em contas_por_mes: {str(e)}")
        return jsonify({
            "error": "Erro ao gerar dados mensais",
            "details": str(e)
        }), 500
    finally:
        if conn:
            conn.close()
@contas_a_pagar_bp.route('/api/categorias_agrupadas')
def categorias_agrupadas():
    try:
        mes = request.args.get("mes")
        ano = request.args.get("ano")

        if not mes or not ano:
            return jsonify({"error": "Parâmetros 'mes' e 'ano' são obrigatórios"}), 400

        try:
            mes_num = int(mes)
            ano_num = int(ano)
            if not (1 <= mes_num <= 12):
                raise ValueError("Mês inválido")
        except ValueError as e:
            return jsonify({"error": "Parâmetros inválidos", "details": str(e)}), 400

        conn = get_db_connection()
        cursor = conn.cursor()

        # Consulta corrigida - removendo TRIM de campos numéricos
        query = """
            SELECT 
                COALESCE(NULLIF(TRIM(categorias), ''), 'Outros') as categoria,
                COALESCE(ABS(SUM(NULLIF(valor, 0)::float)), 0) as total
            FROM contas_a_pagar
            WHERE SUBSTRING(vencimento FROM 4 FOR 7) = %s
              AND categorias IS NOT NULL AND TRIM(categorias) != ''
              AND valor IS NOT NULL
            GROUP BY categoria
            HAVING ABS(SUM(NULLIF(valor, 0)::float)) > 0
            ORDER BY total DESC
        """

        cursor.execute(query, (f"{mes_num:02d}/{ano_num}",))
        resultados = cursor.fetchall()

        dados = []
        for row in resultados:
            try:
                dados.append({
                    "categoria": row[0] if row[0] else 'Outros',
                    "total": abs(float(row[1])) if row[1] is not None else 0.0
                })
            except (TypeError, ValueError) as e:
                current_app.logger.warning(f"Dado inválido ignorado: {row} - {str(e)}")
                continue

        return jsonify(dados)

    except Exception as e:
        current_app.logger.error(f"Erro em categorias_agrupadas: {str(e)}")
        return jsonify({
            "error": "Erro ao processar categorias",
            "details": str(e)
        }), 500
    finally:
        if conn:
            conn.close()


@contas_a_pagar_bp.route('/pdf')
def gerar_pdf_contas():
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        filtro = request.args.get('filtro', 'dia')
        mes = request.args.get('mes', str(datetime.today().month))
        ano = request.args.get('ano', str(datetime.today().year))
        hoje = datetime.today().date()
        titulo_param = request.args.get('titulo')

        # Títulos padrão para cada filtro
        titulos = {
            'dia': "CONTAS DO DIA",
            'today': "CONTAS A PAGAR HOJE",
            'atrasados': "CONTAS ATRASADAS",
            'segunda': "CONTAS SEGUNDA + FIM DE SEMANA",
            'all': "TODAS AS CONTAS A PAGAR",
            'paid': "CONTAS PAGAS",
            'balance': "CONTAS EM ABERTO"
        }
        titulo = titulos.get(filtro, "RELATÓRIO DE CONTAS")

        query = """
            SELECT vencimento, fornecedor, categorias, plano_de_contas,
                   valor, valor_pago, codigo
            FROM contas_a_pagar
        """
        params = []

        # Filtros específicos
        if filtro in ['dia', 'today']:
            query += " WHERE TO_DATE(vencimento, 'DD/MM/YYYY') = CURRENT_DATE"
        elif filtro == 'atrasados':
            query += """
                WHERE (valor_pago IS NULL OR valor_pago = 0)
                AND TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
            """
        elif filtro == 'segunda':
            if hoje.weekday() == 0:  # Segunda-feira
                sabado = hoje - timedelta(days=2)
                domingo = hoje - timedelta(days=1)
                segunda = hoje
            else:
                dias_para_segunda = (0 - hoje.weekday()) % 7
                segunda = hoje + timedelta(days=dias_para_segunda)
                sabado = segunda - timedelta(days=2)
                domingo = segunda - timedelta(days=1)

            query += """
                WHERE (
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
        elif filtro == 'paid':
            query += " WHERE valor_pago > 0"
        elif filtro == 'balance':
            query += " WHERE (valor_pago IS NULL OR valor_pago = 0)"

        # Filtro adicional por mês/ano
        if mes and ano and filtro not in ['dia', 'today', 'atrasados', 'segunda']:
            if 'WHERE' in query:
                query += " AND"
            else:
                query += " WHERE"
            query += " SUBSTRING(vencimento FROM 4 FOR 7) = %s"
            params.append(f"{int(mes):02d}/{ano}")

        cursor.execute(query, params)
        lancamentos = []
        for row in cursor.fetchall():
            try:
                lancamentos.append({
                    "vencimento": row[0] or '-',
                    "fornecedor": row[1] or '-',
                    "categoria": row[2] or '-',
                    "plano": row[3] or '-',
                    "valor": abs(float(row[4])) if row[4] is not None else 0.0,
                    "pago": abs(float(row[5])) if row[5] is not None else 0.0,
                    "status": calcular_status(row[0], row[5])
                })
            except (TypeError, ValueError) as e:
                current_app.logger.warning(f"Registro PDF inválido ignorado: {row} - {str(e)}")
                continue

        # Título customizado se fornecido
        if titulo_param:
            titulo = titulo_param

        # Geração do PDF
        html = render_template(
            "contas_pdf.html",
            lancamentos=lancamentos,
            titulo=titulo,
            data_emissao=datetime.now().strftime("%d/%m/%Y %H:%M"),
            total_geral=sum(abs(item['valor']) for item in lancamentos)
        )

        pdf = HTML(string=html).write_pdf()
        if not pdf:
            raise ValueError("Falha ao gerar PDF")

        response = make_response(pdf)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=contas_a_pagar_{filtro}.pdf'
        return response

    except Exception as e:
        current_app.logger.error(f"Erro ao gerar PDF: {str(e)}")
        abort(500, description="Erro ao gerar relatório PDF")
    finally:
        if conn:
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
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

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
