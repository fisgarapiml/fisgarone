from flask import Blueprint, render_template, request, jsonify, current_app, make_response, abort
import json
from datetime import datetime, timedelta, date
import pandas as pd
import re
from weasyprint import HTML
from utils.conexao_postgres import get_db_connection
import psycopg2.extras

contas_a_pagar_bp = Blueprint('contas_a_pagar_bp', __name__)

class ContasPagarIntegracao:
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)  # Inicializa integração com Flask

    def init_app(self, app):
        # Associa a extensão à aplicação
        app.extensions['contas_pagar_integracao'] = self



        # CHAMA ATUALIZAÇÃO AUTOMÁTICA AO INICIAR
        self.atualizar_dados_automaticamente()

    def atualizar_dados_automaticamente(self):
        """
        Executa atualização automática dos dados ao iniciar o app.
        Se precisar rodar outra rotina, coloque aqui!
        """
        print("Rodando atualização automática de contas a pagar")
        # Exemplo de chamada real (descomente e adapte à sua lógica)
        # with self.app.app_context():
        #     self.atualizar_dados()

    # Restante da classe continua aqui...
    # def criar_tabela_se_nao_existir(self): ...
    # def atualizar_dados(self): ...


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


# ----------------------------
# FUNÇÕES AUXILIARES
# ----------------------------

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
            df[col] = df[col].astype(str).str.replace(",", ".").str.replace(r'[^\d.]', '', regex=True)
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'valor' in df.columns:
        df['valor'] = df['valor'].apply(lambda x: -abs(x))
    df.drop_duplicates(inplace=True)
    print("✅ Dados processados com sucesso.")
    return df


def formatar_brl(valor):
    """Formata o valor para o padrão BRL: R$ 1.234,56"""
    try:
        valor_float = float(valor)
        return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"


def calcular_status(vencimento, valor_pago):
    """Retorna o status do lançamento ('Pago', 'Vencido', 'Hoje', 'Pendente')"""
    hoje = date.today()

    try:
        # Converter valor_pago para float seguro
        if valor_pago in [None, '', '0', 0]:
            valor_pago_float = 0.0
        else:
            valor_pago_float = abs(float(valor_pago))
    except (ValueError, TypeError):
        valor_pago_float = 0.0

    try:
        # Parse da data de vencimento
        if isinstance(vencimento, str):
            dia, mes, ano = map(int, vencimento.split("/"))
            data_vencimento = date(ano, mes, dia)
        elif isinstance(vencimento, date):
            data_vencimento = vencimento
        else:
            return "Pendente"
    except Exception:
        return "Pendente"

    # Verificar se está pago (considerando pagamentos parciais)
    if valor_pago_float > 0:
        return "Pago"
    elif data_vencimento < hoje:
        return "Vencido"
    elif data_vencimento == hoje:
        return "Hoje"
    else:
        return "Pendente"


# ----------------------------
# ROTAS PRINCIPAIS
# ----------------------------

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
        mes_corrente = f"{mes_param:02d}/{ano_param}"

        # Query para daily_data (dados por dia)
        cursor.execute("""
            SELECT
                SUBSTRING(vencimento FROM 1 FOR 2) as dia,
                SUM(ABS(valor::numeric)) as total,
                CASE
                    WHEN TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
                         AND (valor_pago IS NULL OR valor_pago::numeric = 0) THEN 'overdue'
                    WHEN valor_pago::numeric > 0 THEN 'paid'
                    ELSE 'pending'
                END as status
            FROM contas_a_pagar
            WHERE SUBSTRING(vencimento FROM 4 FOR 7) = %s
            GROUP BY SUBSTRING(vencimento FROM 1 FOR 2),
                     CASE
                        WHEN TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
                             AND (valor_pago IS NULL OR valor_pago::numeric = 0) THEN 'overdue'
                        WHEN valor_pago::numeric > 0 THEN 'paid'
                        ELSE 'pending'
                     END
            ORDER BY dia
        """, (mes_corrente,))

        daily_data = {}
        for row in cursor.fetchall():
            dia = row['dia']
            total = float(row['total']) if row['total'] is not None else 0.0
            status = row['status']

            if dia in daily_data:
                daily_data[dia]['total'] += total
                if status == 'overdue' or (status == 'pending' and daily_data[dia]['status'] == 'paid'):
                    daily_data[dia]['status'] = status
            else:
                daily_data[dia] = {'total': total, 'status': status}

        # Preenche todos os dias do mês
        complete_daily_data = {}
        for day in range(1, 32):
            dia_str = f"{day:02d}"
            complete_daily_data[dia_str] = daily_data.get(dia_str, {'total': 0.0, 'status': 'none'})

        # Consultas para os cards (NÃO use ABS no SQL se já salva negativo)
        def get_sql_result(query, params=()):
            cursor.execute(query, params)
            result = cursor.fetchone()
            if result is None:
                return 0.0
            value = list(result.values())[0] if isinstance(result, dict) else result[0]
            try:
                return abs(float(value)) if value is not None else 0.0
            except (ValueError, TypeError):
                return 0.0

        # Total Previsto do mês (a pagar)
        total_previsto = get_sql_result("""
            SELECT COALESCE(SUM(valor), 0) FROM contas_a_pagar
            WHERE SUBSTRING(vencimento FROM 4 FOR 7) = %s
        """, (mes_corrente,))

        # Total Pago do mês
        total_pago = get_sql_result("""
            SELECT COALESCE(SUM(valor_pago), 0) FROM contas_a_pagar
            WHERE SUBSTRING(vencimento FROM 4 FOR 7) = %s
              AND valor_pago IS NOT NULL AND valor_pago > 0
        """, (mes_corrente,))

        # Saldo
        saldo = total_pago + total_previsto

        # Atrasados (todos os meses, NÃO só mês atual)
        valor_vencido_total = get_sql_result("""
            SELECT COALESCE(SUM(valor), 0) FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
              AND TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
        """)

        # A Pagar Hoje
        valor_hoje_total = get_sql_result("""
            SELECT COALESCE(SUM(valor), 0) FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
              AND TO_DATE(vencimento, 'DD/MM/YYYY') = CURRENT_DATE
        """)

        # Query para lançamentos
        query_lancamentos = """
            SELECT codigo, vencimento, categorias, fornecedor, plano_de_contas, 
                   valor, valor_pago, comentario
            FROM contas_a_pagar
            WHERE 1=1
        """
        params = []

        if filtro == "atrasados":
            titulo_lancamentos = "Contas Vencidas"
            query_lancamentos += """
                AND (valor_pago IS NULL OR valor_pago::numeric = 0)
                AND TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
            """
        elif filtro == "hoje":
            titulo_lancamentos = "Contas a Pagar Hoje"
            query_lancamentos += """
                AND (valor_pago IS NULL OR valor_pago::numeric = 0)
                AND TO_DATE(vencimento, 'DD/MM/YYYY') = CURRENT_DATE
            """
        else:
            query_lancamentos += " AND SUBSTRING(vencimento FROM 4 FOR 7) = %s"
            params.append(mes_corrente)
            if dia_param:
                query_lancamentos += " AND SUBSTRING(vencimento FROM 1 FOR 2) = %s"
                params.append(f"{int(dia_param):02d}")
                titulo_lancamentos = f"Lançamentos do dia {dia_param.zfill(2)}/{mes_corrente[-4:]}"
            else:
                titulo_lancamentos = f"Lançamentos de {mes_corrente}"

        query_lancamentos += " ORDER BY TO_DATE(vencimento, 'DD/MM/YYYY') ASC"
        cursor.execute(query_lancamentos, params)

        lancamentos = []
        for row in cursor.fetchall():
            try:
                valor = abs(float(row['valor'])) if row['valor'] is not None else 0.0
                valor_pago = abs(float(row['valor_pago'])) if row['valor_pago'] not in [None, '', '0', 0] else 0.0

                lancamentos.append({
                    "codigo": row['codigo'],
                    "vencimento": row['vencimento'] or '-',
                    "categoria": row['categorias'] or '-',
                    "fornecedor": row['fornecedor'] or '-',
                    "plano": row['plano_de_contas'] or '-',
                    "valor": valor,
                    "pago": valor_pago,
                    "status": calcular_status(row['vencimento'], row['valor_pago']),
                    "comentario": row['comentario'] or ''
                })
            except (TypeError, ValueError) as e:
                current_app.logger.warning(f"Registro inválido ignorado: {row} - {str(e)}")
                continue

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
            mes_corrente=mes_corrente,
            filtro_atual=filtro
        )

    except Exception as e:
        current_app.logger.error(f"Erro em contas_a_pagar: {str(e)}")
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
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = """
            SELECT codigo, vencimento, categorias, fornecedor, plano_de_contas, 
                   valor, valor_pago, comentario
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
                query += " AND valor_pago::numeric > 0"
            elif valor == 'balance':
                query += " AND (valor_pago IS NULL OR valor_pago::numeric = 0)"
            elif valor == 'overdue':
                query += """
                    AND (valor_pago IS NULL OR valor_pago::numeric = 0)
                    AND TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
                """
            elif valor == 'today':
                query += """
                    AND (valor_pago IS NULL OR valor_pago::numeric = 0)
                    AND TO_DATE(vencimento, 'DD/MM/YYYY') = CURRENT_DATE
                """

            if mes and ano:
                query += " AND SUBSTRING(vencimento FROM 4 FOR 7) = %s"
                params.append(f"{int(mes):02d}/{ano}")

        query += " ORDER BY TO_DATE(vencimento, 'DD/MM/YYYY') ASC"
        cursor.execute(query, params)

        lancamentos = []
        for row in cursor.fetchall():
            try:
                valor = abs(float(row['valor'])) if row['valor'] is not None else 0.0
                valor_pago = abs(float(row['valor_pago'])) if row['valor_pago'] not in [None, '', '0', 0] else 0.0

                lancamentos.append({
                    "codigo": row['codigo'],
                    "vencimento": row['vencimento'] or '-',
                    "categoria": row['categorias'] or '-',
                    "fornecedor": row['fornecedor'] or '-',
                    "plano": row['plano_de_contas'] or '-',
                    "valor": valor,
                    "pago": valor_pago,
                    "status": calcular_status(row['vencimento'], row['valor_pago']),
                    "comentario": row['comentario'] or ''
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
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = """
            SELECT 
                SUBSTRING(vencimento FROM 4 FOR 7) as mes_ano,
                COALESCE(SUM(ABS(valor::numeric)), 0) as total_previsto,
                COALESCE(SUM(ABS(valor_pago::numeric)), 0) as total_pago
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
                    "mes": row['mes_ano'] if row['mes_ano'] else '00/0000',
                    "previsto": abs(float(row['total_previsto'])) if row['total_previsto'] is not None else 0.0,
                    "pago": abs(float(row['total_pago'])) if row['total_pago'] is not None else 0.0
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
    conn = None
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
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        query = """
            SELECT 
                COALESCE(NULLIF(TRIM(categorias), ''), 'Outros') as categoria,
                COALESCE(SUM(ABS(valor::numeric)), 0) as total
            FROM contas_a_pagar
            WHERE SUBSTRING(vencimento FROM 4 FOR 7) = %s
              AND categorias IS NOT NULL AND TRIM(categorias) != ''
              AND valor IS NOT NULL
            GROUP BY categoria
            HAVING SUM(ABS(valor::numeric)) > 0
            ORDER BY total DESC
        """

        cursor.execute(query, (f"{mes_num:02d}/{ano_num}",))
        resultados = cursor.fetchall()

        dados = []
        for row in resultados:
            try:
                dados.append({
                    "categoria": row['categoria'] if row['categoria'] else 'Outros',
                    "total": abs(float(row['total'])) if row['total'] is not None else 0.0
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
        cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        filtro = request.args.get('filtro', 'dia')
        mes = request.args.get('mes', str(datetime.today().month))
        ano = request.args.get('ano', str(datetime.today().year))
        hoje = datetime.today().date()
        titulo_param = request.args.get('titulo')

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

        if filtro in ['dia', 'today']:
            query += " WHERE TO_DATE(vencimento, 'DD/MM/YYYY') = CURRENT_DATE"
        elif filtro == 'atrasados':
            query += """
                WHERE (valor_pago IS NULL OR valor_pago::numeric = 0)
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
            query += " WHERE valor_pago::numeric > 0"
        elif filtro == 'balance':
            query += " WHERE (valor_pago IS NULL OR valor_pago::numeric = 0)"

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
                    "vencimento": row['vencimento'] or '-',
                    "fornecedor": row['fornecedor'] or '-',
                    "categoria": row['categorias'] or '-',
                    "plano": row['plano_de_contas'] or '-',
                    "valor": abs(float(row['valor'])) if row['valor'] is not None else 0.0,
                    "pago": abs(float(row['valor_pago'])) if row['valor_pago'] not in [None, '', '0', 0] else 0.0,
                    "status": calcular_status(row['vencimento'], row['valor_pago']),
                    "codigo": row['codigo']
                })
            except (TypeError, ValueError) as e:
                current_app.logger.warning(f"Registro PDF inválido ignorado: {row} - {str(e)}")
                continue

        if titulo_param:
            titulo = titulo_param

        html = render_template(
            "contas_pdf.html",
            lancamentos=lancamentos,
            titulo=titulo,
            data_emissao=datetime.now().strftime("%d/%m/%Y %H:%M"),
            total_geral=sum(item['valor'] for item in lancamentos)
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
    dados = request.get_json() or request.form.to_dict()
    codigo = dados.pop('codigo', None)
    if not codigo:
        return jsonify(success=False, error='Código não fornecido'), 400

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
        cursor.execute("""
            SELECT
                SUBSTRING(vencimento FROM 1 FOR 2) as day,
                SUM(ABS(valor::numeric)) as total,
                CASE
                    WHEN TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
                         AND (valor_pago IS NULL OR valor_pago::numeric = 0) THEN 'overdue'
                    WHEN valor_pago::numeric > 0 THEN 'paid'
                    ELSE 'pending'
                END as status
            FROM contas_a_pagar
            WHERE SUBSTRING(vencimento FROM 4 FOR 2) = %s
              AND SUBSTRING(vencimento FROM 7 FOR 4) = %s
            GROUP BY day, 
                CASE
                    WHEN TO_DATE(vencimento, 'DD/MM/YYYY') < CURRENT_DATE
                         AND (valor_pago IS NULL OR valor_pago::numeric = 0) THEN 'overdue'
                    WHEN valor_pago::numeric > 0 THEN 'paid'
                    ELSE 'pending'
                END
            ORDER BY day
        """, (f"{int(mes):02d}", ano))

        daily_data = {}
        for row in cursor.fetchall():
            day = row['day']
            total = abs(float(row['total'])) if row['total'] is not None else 0.0
            status = row['status']

            if day in daily_data:
                daily_data[day]['total'] += total
                if status == 'overdue' or (status == 'pending' and daily_data[day]['status'] == 'paid'):
                    daily_data[day]['status'] = status
            else:
                daily_data[day] = {'total': total, 'status': status}

        complete_daily_data = {}
        for day in range(1, 32):
            day_str = f"{day:02d}"
            complete_daily_data[day_str] = daily_data.get(day_str, {'total': 0.0, 'status': 'none'})

        return jsonify(complete_daily_data)

    except Exception as e:
        current_app.logger.error(f"Erro em api_daily_timeline: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()