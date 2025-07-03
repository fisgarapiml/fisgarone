from flask import Blueprint, render_template, request, jsonify, current_app, make_response, abort
import sqlite3
import json
from datetime import datetime, timedelta
import pandas as pd
import re
from weasyprint import HTML

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

def garantir_colunas_no_banco(df, banco, tabela):
    conn = sqlite3.connect(banco)
    cursor = conn.cursor()
    cursor.execute(f"PRAGMA table_info({tabela})")
    colunas_existentes = [info[1] for info in cursor.fetchall()]
    for coluna in df.columns:
        if coluna not in colunas_existentes:
            cursor.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} TEXT")
            print(f"✅ Coluna adicionada: {coluna}")
    conn.commit()
    conn.close()

def importar_para_sqlite(df, banco_dados):
    conn = sqlite3.connect(banco_dados)
    cursor = conn.cursor()
    colunas_insert = ", ".join([f'"{col}"' for col in df.columns])
    placeholders = ", ".join(["?" for _ in df.columns])
    for _, row in df.iterrows():
        cursor.execute(f'''
            INSERT INTO contas_a_pagar ({colunas_insert}) VALUES ({placeholders})
            ON CONFLICT(codigo) DO UPDATE SET
            {", ".join([f'{col} = EXCLUDED.{col}' for col in df.columns if col != "codigo"])};
        ''', tuple(row))
    conn.commit()
    conn.close()
    print("✅ Dados importados com sucesso no banco SQLite.")

def get_db_connection():
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def atualizar_dados_contas_a_pagar():
    sheet_id = "1zj7fuvta2T55G0-cPnWthEfrVnqaui9u2EJ2cBJp64M"
    aba = "compras"
    df = carregar_planilha_google_sheets(sheet_id, aba)
    if df is not None:
        df_processado = processar_dados(df)
        if df_processado is not None:
            garantir_colunas_no_banco(df_processado, current_app.config['DATABASE'], "contas_a_pagar")
            importar_para_sqlite(df_processado, current_app.config['DATABASE'])

@contas_a_pagar_bp.route("/")
def contas_a_pagar():
    #atualizar_dados_contas_a_pagar()

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
            query_lancamentos += " AND substr(vencimento, 4, 7) = ?"
            params.append(mes_corrente)
            if dia_param:
                query_lancamentos += " AND substr(vencimento, 1, 2) = ?"
                params.append(f"{int(dia_param):02d}")
                titulo_lancamentos = f"Lançamentos do dia {dia_param.zfill(2)}/{mes_corrente[-4:]}"
            else:
                titulo_lancamentos = f"Lançamentos de {mes_corrente}"

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
            "financeiro/contas_a_pagar.html",
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
            substr(vencimento, 4, 7) as mes_ano,
            SUM(CAST(valor AS FLOAT)) as total_previsto,
            SUM(CAST(COALESCE(valor_pago, 0) AS FLOAT)) as total_pago
        FROM contas_a_pagar
        GROUP BY mes_ano
        ORDER BY substr(vencimento, 7, 4), substr(vencimento, 4, 2)
    """)

    dados = [
        {"mes": row["mes_ano"], "previsto": abs(row["total_previsto"]), "pago": abs(row["total_pago"])}
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
            WHERE substr(vencimento, 4, 7) = ?
              AND categorias IS NOT NULL AND TRIM(categorias) != ''
              AND valor IS NOT NULL AND TRIM(valor) != ''
            GROUP BY categorias
            HAVING total > 0
            ORDER BY total DESC
        """, (mes_corrente,))
    elif ano:
        cursor.execute("""
            SELECT categorias, SUM(ABS(CAST(valor AS FLOAT))) as total
            FROM contas_a_pagar
            WHERE substr(vencimento, 7, 4) = ?
              AND categorias IS NOT NULL AND TRIM(categorias) != ''
              AND valor IS NOT NULL AND TRIM(valor) != ''
            GROUP BY categorias
            HAVING total > 0
            ORDER BY total DESC
        """, (ano,))
    else:
        cursor.execute("""
            SELECT categorias, SUM(ABS(CAST(valor AS FLOAT))) as total
            FROM contas_a_pagar
            WHERE categorias IS NOT NULL AND TRIM(categorias) != ''
              AND valor IS NOT NULL AND TRIM(valor) != ''
            GROUP BY categorias
            HAVING total > 0
            ORDER BY total DESC
        """)

    resultado = [{"categoria": row["categorias"], "total": row["total"]} for row in cursor.fetchall()]
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
        query += " AND LOWER(categorias) = LOWER(?)"
        params.append(valor)
        if mes and ano:
            query += " AND substr(vencimento, 4, 7) = ?"
            params.append(f"{int(mes):02d}/{ano}")

    elif tipo == 'mes':
        query += " AND substr(vencimento, 4, 7) = ?"
        params.append(valor)

    elif tipo == 'card':
        if valor == 'paid':
            query += " AND valor_pago > 0"
        elif valor == 'balance':
            query += " AND (valor_pago IS NULL OR valor_pago = 0)"
        elif valor == 'overdue':
            query += """
                AND (valor_pago IS NULL OR valor_pago = 0)
                AND date(substr(vencimento, 7, 4) || '-' || 
                         substr(vencimento, 4, 2) || '-' || 
                         substr(vencimento, 1, 2)) < date('now')
            """
        elif valor == 'today':
            query += """
                AND (valor_pago IS NULL OR valor_pago = 0)
                AND date(substr(vencimento, 7, 4) || '-' || 
                         substr(vencimento, 4, 2) || '-' || 
                         substr(vencimento, 1, 2)) = date('now')
            """
        elif valor == 'all':
            pass  # mostra tudo

        if mes and ano:
            query += " AND substr(vencimento, 4, 7) = ?"
            params.append(f"{int(mes):02d}/{ano}")

    query += " ORDER BY vencimento ASC"
    cursor.execute(query, params)

    resultado = [{
        "codigo": row["codigo"],
        "vencimento": row["vencimento"],
        "categoria": row["categorias"] or '-',
        "fornecedor": row["fornecedor"] or '-',
        "plano": row["plano_de_contas"] or '-',
        "valor": float(row["valor"]) if row["valor"] else 0.0,
        "status": calcular_status(row["vencimento"], row["valor_pago"])
    } for row in cursor.fetchall()]

    conn.close()
    return jsonify(resultado)


@contas_a_pagar_bp.route('/pdf')
def gerar_pdf_contas():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Obter parâmetros
        filtro = request.args.get('filtro', 'dia')
        mes = request.args.get('mes', datetime.today().month)
        ano = request.args.get('ano', datetime.today().year)
        hoje = datetime.today().date()

        # Definir consulta base
        query = """
            SELECT vencimento, fornecedor, categorias, plano_de_contas, 
                   valor, valor_pago, codigo
            FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
        """
        params = []

        # Aplicar filtros específicos
        if filtro == "dia":
            titulo = "CONTAS DO DIA"
            query += """
                AND date(substr(vencimento, 7, 4) || '-' || 
                    substr(vencimento, 4, 2) || '-' || 
                    substr(vencimento, 1, 2)) = date('now')
            """
        elif filtro == "atrasados":
            titulo = "CONTAS ATRASADAS"
            query += """
                AND date(substr(vencimento, 7, 4) || '-' || 
                    substr(vencimento, 4, 2) || '-' || 
                    substr(vencimento, 1, 2)) < date('now')
            """
        elif filtro == "segunda":
            titulo = "CONTAS SEGUNDA + FIM DE SEMANA"
            # Calcula datas do fim de semana anterior
            if hoje.weekday() == 0:  # Se hoje é segunda
                sabado = hoje - timedelta(days=2)
                domingo = hoje - timedelta(days=1)
            else:
                # Encontra a próxima segunda
                dias_para_segunda = (0 - hoje.weekday()) % 7
                proxima_segunda = hoje + timedelta(days=dias_para_segunda)
                sabado = proxima_segunda - timedelta(days=2)
                domingo = proxima_segunda - timedelta(days=1)

            query += """
                AND (
                    date(substr(vencimento, 7, 4) || '-' || 
                        substr(vencimento, 4, 2) || '-' || 
                        substr(vencimento, 1, 2)) = date(?)
                    OR
                    date(substr(vencimento, 7, 4) || '-' || 
                        substr(vencimento, 4, 2) || '-' || 
                        substr(vencimento, 1, 2)) = date(?)
                    OR
                    date(substr(vencimento, 7, 4) || '-' || 
                        substr(vencimento, 4, 2) || '-' || 
                        substr(vencimento, 1, 2)) = date(?)
                )
            """
            params.extend([
                hoje.strftime('%Y-%m-%d') if hoje.weekday() == 0 else proxima_segunda.strftime('%Y-%m-%d'),
                sabado.strftime('%Y-%m-%d'),
                domingo.strftime('%Y-%m-%d')
            ])

        cursor.execute(query, params)

        # Processar resultados
        lancamentos = []
        for row in cursor.fetchall():
            lancamentos.append({
                "vencimento": row['vencimento'],
                "fornecedor": row['fornecedor'] or '-',
                "categoria": row['categorias'] or '-',
                "plano": row['plano_de_contas'] or '-',
                "valor": float(row['valor']) if row['valor'] else 0.0,
                "pago": float(row['valor_pago']) if row['valor_pago'] else 0.0,
                "status": calcular_status(row['vencimento'], row['valor_pago'])
            })

        # Gerar HTML para PDF
        html = render_template(
            "contas_pdf.html",
            lancamentos=lancamentos,
            titulo=titulo,
            data_emissao=datetime.now().strftime("%d/%m/%Y %H:%M"),
            total_geral=sum(abs(item['valor']) for item in lancamentos)
        )

        # Criar PDF
        pdf = HTML(string=html).write_pdf()

        # Retornar PDF
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

    # Monta dinamicamente a parte SET do UPDATE
    campos = [f"{campo} = ?" for campo in dados.keys()]
    valores = list(dados.values())
    valores.append(codigo)

    conn = sqlite3.connect(current_app.config['DATABASE'])
    try:
        conn.execute(
            f"UPDATE contas_a_pagar SET {', '.join(campos)} WHERE codigo = ?",
            valores
        )
        conn.commit()
    except Exception as e:
        return jsonify(success=False, error=str(e)), 500
    finally:
        conn.close()

    return jsonify(success=True)

