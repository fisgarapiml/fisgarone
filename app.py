from flask import Flask, render_template, request, jsonify, redirect, url_for, make_response, flash
from werkzeug.utils import secure_filename
import os
import sqlite3
import xml.etree.ElementTree as ET
from datetime import datetime
import csv
import io
import json
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)
app.secret_key = 'fisgarone123'

app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Configurações
DB = 'grupo_fisgar.db'
PASTA_XML = 'compras_xml'
NAMESPACE = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

def get_db_connection():
    """Cria e retorna uma conexão com o banco de dados"""
    conn = sqlite3.connect("C:/sistema_financeiro/grupo_fisgar.db")
    conn.row_factory = sqlite3.Row  # Converte para dicionário
    return conn

# Funções auxiliares
def formatar_brl(valor):
    """Formata valores monetários no padrão brasileiro"""
    try:
        valor_float = float(valor) if valor is not None else 0.0
        return f"R$ {valor_float:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "R$ 0,00"

def calcular_status(vencimento_str, valor_pago):
    """Calcula o status do lançamento baseado na data de vencimento e se foi pago"""
    if valor_pago and float(valor_pago) > 0:
        return 'paid'
# --------------------------------------------
# 🛠️ FUNÇÕES DE BANCO DE DADOS E PROCESSAMENTO
# --------------------------------------------

def criar_tabelas():
    """Cria todas as tabelas necessárias"""
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()

        # Tabela unificada de produtos
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS produtos (
                        codigo INTEGER PRIMARY KEY AUTOINCREMENT,
                        codigo_fornecedor TEXT UNIQUE,
                        nome TEXT,
                        unidade_compra TEXT,
                        quantidade INTEGER,
                        valor_total REAL,
                        ipi REAL,
                        qtd_volumes INTEGER,
                        qtd_por_volume INTEGER,
                        qtd_real_unidades INTEGER,
                        custo_volume REAL,
                        custo_unitario REAL,
                        custo_com_ipi REAL,
                        fornecedor TEXT,
                        numero_nfe TEXT,
                        data_emissao TEXT,
                        caminho_xml TEXT,
                        status TEXT DEFAULT 'pendente',
                        origem TEXT DEFAULT 'nfe',
                        data_cadastro TEXT DEFAULT CURRENT_TIMESTAMP,
                        data_atualizacao TEXT DEFAULT CURRENT_TIMESTAMP
                    )
        """)

        # Tabela de NF-e processadas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS nfe_processadas (
                codigo INTEGER PRIMARY KEY AUTOINCREMENT,
                numero_nfe TEXT,
                fornecedor TEXT,
                data_emissao TEXT,
                valor_total REAL,
                caminho_xml TEXT,
                data_processamento TEXT
            )
        """)

        # Tabela de produtos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS produtos (
                codigo INTEGER PRIMARY KEY AUTOINCREMENT,
                fornecedor TEXT UNIQUE,
                nome TEXT,
                unidade_compra TEXT,
                quantidade INTEGER,
                valor_total REAL,
                ipi REAL,
                fator_conversao INTEGER DEFAULT 1,
                custo_unitario REAL,
                custo_com_ipi REAL,
                atualizado_em TEXT,
                categorias TEXT,
                status TEXT
            )
        """)

        # Tabela de contas a pagar
        cursor.execute("""
                    CREATE TABLE IF NOT EXISTS contas_a_pagar (
                        codigo INTEGER PRIMARY KEY AUTOINCREMENT,
                        vencimento TEXT,
                        agendamento TEXT,
                        fornecedor TEXT,
                        banco_pagamento TEXT,
                        banco_previsto TEXT,
                        valor REAL,
                        valor_pendente REAL,
                        valor_pago REAL,
                        documento TEXT,
                        documento_tipo TEXT,
                        pagamento_tipo TEXT,
                        plano_de_contas TEXT,
                        data_cadastro TEXT,
                        data_competencia TEXT,
                        data_documento TEXT,
                        data_pagamento TEXT,
                        arquivo_pagamento TEXT,
                        arquivo_documento TEXT,
                        arquivo_xml TEXT,
                        arquivo_boleto TEXT,
                        comentario TEXT,
                        recebimento TEXT,
                        codigo_externo TEXT,
                        empresa TEXT,
                        conta TEXT,
                        status TEXT,
                        categorias TEXT,
                        tipo_custo TEXT,
                        centro_de_custo TEXT,
                        tipo TEXT,
                        emissao TEXT,
                        tipo_documento TEXT,
                        tipo_pagamento TEXT
                    )
                """)

        conn.commit()


def extrair_produtos_de_xml(caminho_xml):
    """Extrai dados de produtos de um XML de NF-e"""
    tree = ET.parse(caminho_xml)
    root = tree.getroot()
    produtos = []

    for det in root.findall('.//ns:det', NAMESPACE):
        try:
            prod = det.find('ns:prod', NAMESPACE)
            imposto = det.find('ns:imposto', NAMESPACE)

            produtos.append({
                'codigo_fornecedor': prod.find('ns:cProd', NAMESPACE).text,
                'nome': prod.find('ns:xProd', NAMESPACE).text,
                'unidade_compra': prod.find('ns:uCom', NAMESPACE).text,
                'quantidade': int(float(prod.find('ns:qCom', NAMESPACE).text)),
                'valor_total': round(float(prod.find('ns:vProd', NAMESPACE).text), 2),
                'ipi': round(float(imposto.find('ns:IPI/ns:IPITrib/ns:pIPI', NAMESPACE).text or 0), 2) if imposto.find('ns:IPI/ns:IPITrib/ns:pIPI', NAMESPACE) is not None else 0,
                'fornecedor': root.find('.//ns:xNome', NAMESPACE).text,
                'numero_nfe': root.find('.//ns:ide/ns:nNF', NAMESPACE).text,
                'data_emissao': root.find('.//ns:ide/ns:dhEmi', NAMESPACE).text[:10] if root.find('.//ns:ide/ns:dhEmi', NAMESPACE) is not None else "—",
                'caminho_xml': caminho_xml
            })

        except Exception as e:
            print(f"Erro ao processar produto: {e}")

    return produtos


def get_db():
    conn = sqlite3.connect('grupo_fisgar.db')
    conn.row_factory = sqlite3.Row  # Retorna dicionários
    return conn


# Rota para alimentar os cards (novo endpoint)
@app.route('/api/cards')
def get_cards():
    db = get_db()
    hoje = datetime.now().strftime('%Y-%m-%d')

    dados = db.execute('''
        SELECT 
            SUM(CASE WHEN status != "pago" THEN valor ELSE 0 END) as previsto,
            SUM(CASE WHEN status = "pago" THEN valor ELSE 0 END) as pago,
            SUM(CASE WHEN status != "pago" THEN valor ELSE 0 END) - 
            SUM(CASE WHEN status = "pago" THEN valor ELSE 0 END) as saldo,
            COUNT(CASE WHEN data_vencimento = ? AND status != "pago" THEN 1 END) as hoje,
            COUNT(CASE WHEN data_vencimento < ? AND status != "pago" THEN 1 END) as atrasados
        FROM lancamento_contas_pagar.html
    ''', (hoje, hoje)).fetchone()

    db.close()
    return jsonify(dict(dados))

def ler_xmls_da_pasta(pasta):
    """Lê todos os XMLs de uma pasta e extrai os produtos"""
    produtos_finais = []
    for arquivo in os.listdir(pasta):
        if arquivo.endswith('.xml'):
            caminho = os.path.join(pasta, arquivo)
            produtos_finais.extend(extrair_produtos_de_xml(caminho))
    return produtos_finais


def get_db_connection():
    return sqlite3.connect("grupo_fisgar.db")


def formatar_brl(valor):
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def calcular_status(vencimento, valor_pago):
    hoje = datetime.today().date()
    try:
        dia, mes, ano = map(int, vencimento.split("/"))
        data_vencimento = datetime(ano, mes, dia).date()
    except Exception:
        return "erro"

    if valor_pago and valor_pago > 0:
        return "Pago"
    elif data_vencimento < hoje:
        return "Vencido"
    elif data_vencimento == hoje:
        return "Hoje"
    else:
        return "Pendente"


@app.route("/contas-a-pagar")
def contas_a_pagar():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        hoje = datetime.today()
        mes_param = request.args.get("mes", hoje.month)
        ano_param = request.args.get("ano", hoje.year)
        filtro = request.args.get("filtro", "mes")
        mes_corrente = f"{int(mes_param):02d}/{ano_param}"

        # Timeline diária por status
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

        # Preenche dias vazios
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

        saldo = total_pago + total_previsto  # valores negativos + positivos

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
            current_month=int(mes_param),
            current_year=int(ano_param),
            mes_corrente=mes_corrente
        )

    except Exception as e:
        print(f"Erro: {str(e)}")
        return render_template("error.html", error=str(e))
    finally:
        conn.close()

@app.route('/home')
def home():
    try:
        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()

            # Dados para os cards
            cursor.execute("SELECT COUNT(*) FROM nfe_processadas")
            total_nfe = cursor.fetchone()[0] or 0

            cursor.execute("SELECT SUM(valor_total) FROM nfe_processadas")
            valor_total = cursor.fetchone()[0] or 0

            cursor.execute("SELECT COUNT(DISTINCT fornecedor) FROM nfe_processadas")
            total_fornecedores = cursor.fetchone()[0] or 0

            return render_template('home.html',
                                   total_nfe=total_nfe,
                                   valor_total=valor_total,
                                   total_fornecedores=total_fornecedores,
                                   now=datetime.now())

    except Exception as e:
        print(f"Erro na rota home: {str(e)}")
        return "Erro ao carregar a página principal", 500
@app.route('/nfe')
def painel_nfe():
    """Painel de processamento de NF-e"""
    produtos = ler_xmls_da_pasta(PASTA_XML)
    return render_template('painel_nfe.html',
                           produtos=produtos,
                           total_produtos=len(produtos),
                           valor_total=sum(p['valor_total'] for p in produtos),
                           fornecedores_unicos=list(set(p['fornecedor'] for p in produtos)),
                           numeros_nfe=list(set(p['numero_nfe'] for p in produtos)))


@app.route('/salvar-produto', methods=['POST'])
def salvar_produto():
    """Salva um produto no banco de dados"""
    try:
        dados = request.json

        # Validação básica
        required_fields = ['id', 'codigo_fornecedor', 'nome', 'qtd_volumes', 'qtd_por_volume',
                           'numero_nfe', 'fornecedor', 'valor_total', 'ipi', 'quantidade']
        for field in required_fields:
            if field not in dados:
                return jsonify({'status': 'error', 'message': f'Campo obrigatório faltando: {field}'}), 400

        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()

            # Calcula os valores
            custo_volume = float(dados['valor_total']) / int(dados['qtd_volumes'])
            custo_unitario = custo_volume / int(dados['qtd_por_volume'])
            custo_com_ipi = custo_unitario * (1 + (float(dados['ipi']) / 100))
            qtd_real_unidades = int(dados['qtd_volumes']) * int(dados['qtd_por_volume'])

            # Insere ou atualiza na tabela unificada
            cursor.execute("""
                INSERT OR REPLACE INTO produtos (
                    codigo_fornecedor, nome, unidade_compra, quantidade, valor_total, ipi,
                    qtd_volumes, qtd_por_volume, qtd_real_unidades,
                    custo_volume, custo_unitario, custo_com_ipi,
                    fornecedor, numero_nfe, data_emissao, caminho_xml, status, origem,
                    data_atualizacao
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados['codigo_fornecedor'],
                dados['nome'],
                dados.get('unidade_compra', 'UN'),
                int(dados['quantidade']),
                float(dados['valor_total']),
                float(dados['ipi']),
                int(dados['qtd_volumes']),
                int(dados['qtd_por_volume']),
                qtd_real_unidades,
                custo_volume,
                custo_unitario,
                custo_com_ipi,
                dados['fornecedor'],
                dados['numero_nfe'],
                dados.get('data_emissao', datetime.now().strftime('%Y-%m-%d')),
                dados.get('caminho_xml', ''),
                'salvo',
                'nfe',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))

            conn.commit()

        return jsonify({
            'status': 'success',
            'message': 'Produto salvo com sucesso',
            'data': {
                'custo_volume': custo_volume,
                'custo_unitario': custo_unitario,
                'custo_com_ipi': custo_com_ipi
            }
        })

    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Erro ao salvar produto: {str(e)}'
        }), 500

@app.route('/estoque')
def estoque():
    conn = get_db_connection()
    try:
        # Dados para os cards
        cursor = conn.cursor()
        cursor.execute('''
            SELECT 
                COUNT(*) as total_itens,
                SUM(CASE WHEN estoque_atual > estoque_minimo THEN 1 ELSE 0 END) as itens_ok,
                SUM(CASE WHEN estoque_atual > 0 AND estoque_atual <= estoque_minimo THEN 1 ELSE 0 END) as itens_baixos,
                SUM(CASE WHEN estoque_atual = 0 THEN 1 ELSE 0 END) as itens_esgotados
            FROM produtos
        ''')
        cards_data = cursor.fetchone()

        # Itens críticos
        cursor.execute('''
            SELECT p.codigo, p.nome, p.categoria, f.nome as fornecedor, 
                   p.estoque_atual, p.estoque_minimo,
                   CASE 
                       WHEN p.estoque_atual = 0 THEN 'Esgotado'
                       WHEN p.estoque_atual <= p.estoque_minimo THEN 'Crítico'
                       ELSE 'OK'
                   END as status,
                   (SELECT MAX(data) FROM movimentacoes WHERE produto_id = p.id AND tipo = 'entrada') as ultima_entrada
            FROM produtos p
            LEFT JOIN fornecedores f ON p.fornecedor_id = f.id
            WHERE p.estoque_atual <= p.estoque_minimo
            ORDER BY p.estoque_atual ASC
            LIMIT 50
        ''')
        itens_criticos = [dict(row) for row in cursor.fetchall()]

        # Dados para gráficos (simplificado)
        meses = ['Jan', 'Fev', 'Mar']
        entradas = [120, 190, 170]
        saidas = [80, 120, 140]
        categorias = ['Eletrônicos', 'Materiais']
        valores = [12000, 5000]

        return render_template('estoque.html',
                               cards_data=cards_data,
                               itens_criticos=itens_criticos,
                               meses=json.dumps(meses),
                               entradas=json.dumps(entradas),
                               saidas=json.dumps(saidas),
                               categorias=json.dumps(categorias),
                               valores=json.dumps(valores))

    except Exception as e:
        print(f"Erro na rota estoque: {str(e)}")
        # Dados de fallback caso ocorra erro
        dados_fallback = {
            'cards_data': {
                'total_itens': 0,
                'itens_ok': 0,
                'itens_baixos': 0,
                'itens_esgotados': 0
            },
            'itens_criticos': [],
            'meses': json.dumps([]),
            'entradas': json.dumps([]),
            'saidas': json.dumps([]),
            'categorias': json.dumps([]),
            'valores': json.dumps([])
        }
        return render_template('estoque.html', **dados_fallback)
    finally:
        conn.close()


@app.route('/produtos')
def produtos_dashboard():
    """Dashboard de produtos"""
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT f.nome AS fornecedor, 
                   p.nome, 
                   p.unidade_medida, 
                   p.estoque_atual, 
                   p.categoria, 
                   p.data_cadastro
            FROM produtos p
            LEFT JOIN fornecedores f ON p.fornecedor_id = f.id
            ORDER BY p.nome
        """)
        produtos = [{
            'fornecedor': p[0],
            'nome': p[1],
            'unidade': p[2],
            'estoque': p[3],
            'categoria': p[4],
            'cadastro': p[5]
        } for p in cursor.fetchall()]

    return render_template("produtos.html", produtos=produtos)


@app.route('/lancamento-manual', methods=['GET', 'POST'])
def lancamento_manual():
    conn = get_db_connection()

    if request.method == 'POST':
        try:
            # Processar dados do formulário
            dados = {
                'vencimento': request.form.get('vencimento'),
                'fornecedor': request.form.get('fornecedor'),
                'banco_pagamento': request.form.get('banco_pagamento'),
                'valor': float(request.form.get('valor', 0)),
                'valor_pago': float(request.form.get('valor_pago', 0)),
                'valor_pendente': float(request.form.get('valor', 0)) - float(request.form.get('valor_pago', 0)),
                'documento': request.form.get('documento'),
                'documento_tipo': request.form.get('tipo_documento'),
                'pagamento_tipo': request.form.get('pagamento_tipo'),
                'plano_de_contas': request.form.get('plano_de_contas'),
                'data_cadastro': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'comentario': request.form.get('comentario'),
                'empresa': request.form.get('empresa'),
                'conta': request.form.get('conta'),
                'status': 'PENDENTE',  # Será atualizado abaixo
                'categorias': request.form.get('categorias'),
                'tipo_custo': request.form.get('tipo_custo'),
                'centro_de_custo': request.form.get('centro_de_custo'),
                'tipo': request.form.get('tipo'),
                'tipo_documento': request.form.get('tipo_documento')
            }

            # Atualizar status baseado nos dados
            if dados['valor_pago'] > 0:
                dados['status'] = 'PAGO'
                dados['data_pagamento'] = datetime.now().strftime('%Y-%m-%d')
            elif dados['vencimento']:
                try:
                    dia, mes, ano = map(int, dados['vencimento'].split('/'))
                    vencimento = datetime(ano, mes, dia).date()
                    if vencimento < datetime.now().date():
                        dados['status'] = 'ATRASADO'
                except:
                    pass

            # Processar uploads de arquivos
            arquivos = ['arquivo_pagamento', 'arquivo_documento', 'arquivo_xml', 'arquivo_boleto']
            for arquivo in arquivos:
                if arquivo in request.files:
                    file = request.files[arquivo]
                    if file and file.filename:
                        filename = secure_filename(file.filename)
                        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                        dados[arquivo] = filename

            # Inserir no banco de dados
            colunas = ', '.join(dados.keys())
            placeholders = ', '.join(['?'] * len(dados))

            conn.execute(f"INSERT INTO contas_a_pagar ({colunas}) VALUES ({placeholders})", tuple(dados.values()))
            conn.commit()

            flash('Lançamento registrado com sucesso!', 'success')
            return redirect(url_for('lancamento_manual'))

        except Exception as e:
            conn.rollback()
            flash(f'Erro ao registrar lançamento: {str(e)}', 'danger')

    # Para requisições GET
    try:
        # Obter opções para selects
        opcoes = {
            'fornecedores': [row[0] for row in conn.execute(
                "SELECT DISTINCT fornecedor FROM contas_a_pagar WHERE fornecedor IS NOT NULL").fetchall()],
            'categorias': [row[0] for row in conn.execute(
                "SELECT DISTINCT categorias FROM contas_a_pagar WHERE categorias IS NOT NULL").fetchall()],
            # Adicione outros campos conforme necessário
        }
        return render_template('lancamento_manual.html', **opcoes)

    except Exception as e:
        flash(f'Erro ao carregar opções: {str(e)}', 'danger')
        return render_template('lancamento_manual.html')

    finally:
        conn.close()


# --------------------------------------------
# 🎛️ FUNÇÕES AUXILIARES (CORRIGIDAS)
# --------------------------------------------

def obter_opcoes_distintas(conn, campo):
    """Obtém valores distintos de um campo na tabela contas_a_pagar"""
    try:
        # Usa aspas para o nome do campo para evitar problemas com espaços
        resultados = conn.execute(
            f'SELECT DISTINCT "{campo}" FROM contas_a_pagar WHERE "{campo}" IS NOT NULL').fetchall()
        return [row[0] for row in resultados if row[0]]
    except sqlite3.Error as e:
        print(f"Erro ao obter opções para {campo}: {str(e)}")
        return []


def calcular_status_contas_pagar(vencimento_str, valor_pago):
    """Calcula o status da conta baseado na data de vencimento e valor pago"""
    try:
        if valor_pago and float(valor_pago) > 0:
            return 'PAGO'

        if not vencimento_str:
            return 'PENDENTE'

        # Converte a data do formato DD/MM/YYYY para objeto date
        partes_data = vencimento_str.split('/')
        if len(partes_data) == 3:
            dia, mes, ano = map(int, partes_data)
            vencimento = datetime(ano, mes, dia).date()
            hoje = datetime.now().date()

            if vencimento < hoje:
                return 'ATRASADO'
        return 'PENDENTE'
    except:
        return 'PENDENTE'

@app.route('/api/contas-a-pagar/opcoes', methods=['GET'])
def obter_opcoes_contas_pagar():
    """Endpoint para obter opções dinâmicas para o formulário"""
    conn = get_db_connection()
    try:
        campo = request.args.get('campo')
        if not campo:
            return jsonify({'status': 'error', 'message': 'Parâmetro "campo" é obrigatório'}), 400

        opcoes = obter_opcoes_distintas(conn, campo)
        return jsonify({'status': 'success', 'opcoes': opcoes})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        conn.close()


@app.route('/api/contas-a-pagar/adicionar-opcao', methods=['POST'])
def adicionar_opcao_contas_pagar():
    """Endpoint para adicionar novas opções dinâmicas"""
    try:
        data = request.json
        campo = data.get('campo')
        valor = data.get('valor')

        if not campo or not valor:
            return jsonify({'status': 'error', 'message': 'Campo e valor são obrigatórios'}), 400

        # Verifica se o campo existe na tabela
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(contas_a_pagar)")
        colunas = [col[1] for col in cursor.fetchall()]

        if campo not in colunas:
            return jsonify({'status': 'error', 'message': 'Campo inválido'}), 400

        # Adiciona a nova opção ao banco (usando um campo genérico)
        cursor.execute(f"""
            INSERT INTO contas_a_pagar ({campo}, data_cadastro) 
            VALUES (?, ?)
            ON CONFLICT({campo}) DO NOTHING
        """, (valor, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        conn.commit()
        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        conn.close()


# --------------------------------------------
# 🎛️ FUNÇÕES AUXILIARES PARA CONTAS A PAGAR
# --------------------------------------------

def obter_opcoes_distintas(conn, campo):
    """Obtém valores distintos de um campo na tabela contas_a_pagar"""
    resultados = conn.execute(f"SELECT DISTINCT {campo} FROM contas_a_pagar WHERE {campo} IS NOT NULL").fetchall()
    return [row[0] for row in resultados]


def calcular_status_contas_pagar(vencimento_str, valor_pago):
    """Calcula o status da conta baseado na data de vencimento e valor pago"""
    if valor_pago and float(valor_pago) > 0:
        return 'PAGO'

    if not vencimento_str:
        return 'PENDENTE'

    try:
        # Converte a data do formato DD/MM/YYYY para objeto date
        dia, mes, ano = map(int, vencimento_str.split('/'))
        vencimento = datetime(ano, mes, dia).date()
        hoje = datetime.now().date()

        if vencimento < hoje:
            return 'ATRASADO'
        return 'PENDENTE'
    except:
        return 'PENDENTE'


# Adicione esta configuração no início do seu app.py (após criar a instância do Flask)
app.config['UPLOAD_FOLDER'] = 'uploads'
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


@app.route('/api/lancamento/opcoes', methods=['GET'])
def obter_opcoes_lancamento():
    """Endpoint para obter opções dinâmicas para o formulário"""
    conn = get_db_connection()
    try:
        campos = request.args.get('campos', '').split(',')
        opcoes = {}

        for campo in campos:
            if campo:
                resultados = conn.execute(
                    f"SELECT DISTINCT {campo} FROM lancamento_contas_pagar.html WHERE {campo} IS NOT NULL").fetchall()
                opcoes[campo] = [row[0] for row in resultados]

        return jsonify(opcoes)

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        conn.close()


@app.route('/api/lancamento/adicionar-opcao', methods=['POST'])
def adicionar_opcao():
    """Endpoint para adicionar novas opções dinâmicas"""
    try:
        data = request.json
        campo = data.get('campo')
        valor = data.get('valor')

        if not campo or not valor:
            return jsonify({'status': 'error', 'message': 'Campo e valor são obrigatórios'}), 400

        # Verifica se o campo existe na tabela
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info(lancamento_contas_pagar.html)")
        colunas = [col[1] for col in cursor.fetchall()]

        if campo not in colunas:
            return jsonify({'status': 'error', 'message': 'Campo inválido'}), 400

        # Adiciona a nova opção ao banco (atualizando um registro existente ou criando novo)
        cursor.execute(f"""
            INSERT INTO lancamento_contas_pagar.html ({campo}, data_inclusao) 
            VALUES (?, ?)
            ON CONFLICT({campo}) DO NOTHING
        """, (valor, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        conn.commit()
        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

    finally:
        conn.close()


# --------------------------------------------
# 🎛️ FUNÇÕES AUXILIARES PARA LANÇAMENTO MANUAL
# --------------------------------------------

def calcular_status(vencimento_str, valor_pago):
    """Calcula o status do lançamento baseado na data de vencimento e valor pago"""
    if valor_pago and float(valor_pago) > 0:
        return 'paid'

    if not vencimento_str:
        return 'pending'

    try:
        # Converte a data do formato DD/MM/YYYY para objeto date
        dia, mes, ano = map(int, vencimento_str.split('/'))
        vencimento = datetime(ano, mes, dia).date()
        hoje = datetime.now().date()

        if vencimento < hoje:
            return 'overdue'
        return 'pending'
    except:
        return 'pending'


@app.route('/financeiro')
def financeiro():
    return render_template('financeiro.html')

    return render_template('financeiro.html', contas_pendentes=contas_pendentes)

# Contas a Pagar - Grupo de rotas

@app.route('/api/contas/nova', methods=['POST'])
def nova_conta():
    """Adiciona nova conta a pagar"""
    try:
        dados = request.json
        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO lancamento_contas_pagar.html 
                (fornecedor, valor, valor_pendente, vencimento, status, documento, categorias, data_inclusao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                dados['fornecedor'],
                dados['valor'],
                dados['valor'],
                dados['vencimento'],
                'PENDENTE',
                dados.get('documento', ''),
                dados.get('categorias', 'Outros'),
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))
            conn.commit()

        socketio.emit('conta_atualizada')
        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/contas/<int:id>/pagar', methods=['PUT'])
def pagar_conta(codigo):
    """Registra pagamento de uma conta"""
    try:
        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE lancamento_contas_pagar.html 
                SET status = 'PAGO', 
                    valor_pendente = 0,
                    data_pagamento = ?
                WHERE codigo = ?
            """, (datetime.now().strftime('%Y-%m-%d'), codigo))
            conn.commit()

        socketio.emit('conta_atualizada')
        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/contas/<int:codigo>', methods=['DELETE'])
def excluir_conta(codigo):
    """Remove uma conta"""
    try:
        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM lancamento_contas_pagar.html WHERE codigo = ?", (codigo,))
            conn.commit()

        socketio.emit('conta_atualizada')
        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

# --------------------------------------------
# 📡 API ENDPOINTS
# --------------------------------------------

@app.route('/api/nfe/processar', methods=['POST'])
def processar_nfe():
    """Processa uma NF-e e salva no banco de dados"""
    dados = request.json
    try:
        with sqlite3.connect(DB) as conn:
            cursor = conn.cursor()

            # Salva a NF-e
            cursor.execute("""
                INSERT INTO nfe_processadas 
                (numero_nfe, fornecedor, data_emissao, valor_total, caminho_xml, data_processamento)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                dados['numero_nfe'],
                dados['fornecedor'],
                dados['data_emissao'],
                dados['valor_total'],
                dados['caminho_xml'],
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ))

            # Processa produtos
            for produto in dados['produtos']:
                cursor.execute("""
                    INSERT OR REPLACE INTO produtos 
                    (codigo_fornecedor, nome, unidade_compra, quantidade, valor_total, ipi, 
                     custo_unitario, custo_com_ipi, atualizado_em, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    produto['codigo_fornecedor'],
                    produto['nome'],
                    produto['unidade_compra'],
                    produto['quantidade'],
                    produto['valor_total'],
                    produto['ipi'],
                    produto['custo_unitario'],
                    produto['custo_com_ipi'],
                    datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'ativo'
                ))

            conn.commit()

        socketio.emit('nfe_processada', {'total': dados['valor_total']})
        return jsonify({'status': 'success'})

    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/contas/filtrar', methods=['POST'])
def filtrar_contas():
    """Filtra contas a pagar"""
    filtro = request.json
    query = "SELECT * FROM lancamento_contas_pagar.html WHERE 1=1"
    params = []

    if filtro.get('status'):
        query += " AND status = ?"
        params.append(filtro['status'])

    if filtro.get('fornecedor'):
        query += " AND fornecedor LIKE ?"
        params.append(f'%{filtro["fornecedor"]}%')

    if filtro.get('data_inicio'):
        query += " AND vencimento >= ?"
        params.append(filtro['data_inicio'])

    if filtro.get('data_fim'):
        query += " AND vencimento <= ?"
        params.append(filtro['data_fim'])

    with sqlite3.connect(DB) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute(query, params)
        contas = [dict(row) for row in cursor.fetchall()]

    return jsonify(contas)

# --------------------------------------------
# 🛠️ FUNCIONALIDADES ADICIONAIS
# --------------------------------------------

@socketio.on('connect')
def handle_connect():
    print('Cliente conectado via WebSocket')


@app.route('/exportar/produtos')
def exportar_produtos():
    """Exporta produtos para CSV"""
    with sqlite3.connect(DB) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM produtos")
        produtos = cursor.fetchall()

    output = io.StringIO()
    writer = csv.writer(output)

    # Cabeçalho
    writer.writerow([i[0] for i in cursor.description])

    # Dados
    writer.writerows(produtos)

    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=produtos.csv'
    response.headers['Content-type'] = 'text/csv'
    return response


# --------------------------------------------
# 🚀 INICIALIZAÇÃO
# --------------------------------------------

if __name__ == "__main__":
    criar_tabelas()
    socketio.run(app, debug=True)