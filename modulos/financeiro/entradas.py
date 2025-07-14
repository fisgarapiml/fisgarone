from flask import Blueprint, render_template, request, jsonify
from datetime import datetime
import sqlite3
import os

DB_PATH = r'C:\fisgarone\fisgarone.db'

bp = Blueprint('financeiro', __name__, url_prefix='/financeiro')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def format_date_to_br(data_str):
    """Converte data de YYYY-MM-DD ou SQL para DD/MM/YYYY"""
    if not data_str:
        return ''
    try:
        if '-' in data_str:
            parts = data_str.split('-')
            if len(parts) == 3:
                return f"{parts[2]}/{parts[1]}/{parts[0]}"
        return data_str
    except:
        return data_str

def format_date_to_sql(data_str):
    """Converte data de DD/MM/YYYY para YYYY-MM-DD"""
    if not data_str:
        return ''
    try:
        if '/' in data_str:
            parts = data_str.split('/')
            if len(parts) == 3:
                return f"{parts[2]}-{parts[1]}-{parts[0]}"
        return data_str
    except:
        return data_str

def get_financial_data(data_ini='', data_fim='', canal='', status='', pedido_id=''):
    where = []
    params = []

    # Filtros convertidos para padrão SQL
    if data_ini:
        data_ini_sql = format_date_to_sql(data_ini)
        where.append(
            "date(substr(data_liberacao, 7, 4) || '-' || substr(data_liberacao, 4, 2) || '-' || substr(data_liberacao, 1, 2)) >= date(?)")
        params.append(data_ini_sql)

    if data_fim:
        data_fim_sql = format_date_to_sql(data_fim)
        where.append(
            "date(substr(data_liberacao, 7, 4) || '-' || substr(data_liberacao, 4, 2) || '-' || substr(data_liberacao, 1, 2)) <= date(?)")
        params.append(data_fim_sql)

    if canal:
        where.append("(LOWER(origem_conta) = LOWER(?) OR LOWER(tipo) = LOWER(?))")
        params.extend([canal, canal])

    if status:
        where.append("LOWER(status) = LOWER(?)")
        params.append(status)

    if pedido_id:
        where.append("pedido_id LIKE ?")
        params.append(f"%{pedido_id}%")

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""

    try:
        with get_db_connection() as conn:
            # Dados consolidados
            cons_query = f"""
                SELECT
    COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN valor_liquido ELSE 0 END), 0) as recebidas,
    COALESCE(SUM(CASE WHEN status != 'COMPLETED' THEN valor_liquido ELSE 0 END), 0) as pendentes,
    COALESCE(SUM(CASE WHEN LOWER(tipo) = 'ml' AND status = 'COMPLETED' THEN valor_liquido ELSE 0 END), 0) as ml,
    COALESCE(SUM(CASE WHEN LOWER(tipo) = 'shopee' THEN valor_liquido ELSE 0 END), 0) as shopee,
    COALESCE(SUM(CASE WHEN date(substr(data_liberacao, 7, 4) || '-' || substr(data_liberacao, 4, 2) || '-' || substr(data_liberacao, 1, 2)) = date('now', 'localtime') AND status = 'COMPLETED' THEN valor_liquido ELSE 0 END), 0) as hoje
FROM entradas_financeiras
{where_clause}

            """
            consolidado = conn.execute(cons_query, params).fetchone()

            # Últimas entradas
            entradas_query = f"""
                SELECT 
                    e.pedido_id,
                    e.origem_conta as canal,
                    e.data_liberacao as data,
                    COALESCE(e.valor_liquido, 0) as valor,
                    e.status
                FROM entradas_financeiras e
                {where_clause}
                ORDER BY date(substr(e.data_liberacao, 7, 4) || '-' || substr(e.data_liberacao, 4, 2) || '-' || substr(e.data_liberacao, 1, 2)) DESC
                LIMIT 20
            """
            entradas = conn.execute(entradas_query, params).fetchall()

            # Evolução diária
            evolucao_query = f"""
                SELECT 
                    e.data_liberacao as data,
                    SUM(COALESCE(e.valor_liquido, 0)) as total
                FROM entradas_financeiras e
                WHERE e.status = 'COMPLETED'
                {f"AND {' AND '.join(where)}" if where else ""}
                GROUP BY e.data_liberacao
                ORDER BY date(substr(e.data_liberacao, 7, 4) || '-' || substr(e.data_liberacao, 4, 2) || '-' || substr(e.data_liberacao, 1, 2))
            """
            evolucao = conn.execute(evolucao_query, params).fetchall()

            # Pizza por canal (origem_conta)
            pizza_query = f"""
                SELECT 
                    origem_conta as canal, 
                    SUM(COALESCE(valor_liquido, 0)) as total
                FROM entradas_financeiras
                WHERE status = 'COMPLETED'
                {f"AND {' AND '.join(where)}" if where else ""}
                GROUP BY origem_conta
            """
            pizza_result = conn.execute(pizza_query, params).fetchall()
            pizza = {row['canal'] if row['canal'] else 'Desconhecido': float(row['total'] or 0) for row in pizza_result}

            # Lista de canais disponíveis
            canais_query = "SELECT DISTINCT origem_conta FROM entradas_financeiras ORDER BY origem_conta"
            canais_raw = conn.execute(canais_query).fetchall()
            canais = [row['origem_conta'] for row in canais_raw if row['origem_conta']]

            return {
                'consolidado': {
                    'recebido': float(consolidado['recebidas'] or 0),
                    'pendente': float(consolidado['pendentes'] or 0),
                    'ml': float(consolidado['ml'] or 0),
                    'shopee': float(consolidado['shopee'] or 0),
                    'hoje': float(consolidado['hoje'] or 0)
                },
                'entradas': [{
                    'pedido_id': e['pedido_id'],
                    'canal': e['canal'] if e['canal'] else 'Desconhecido',
                    'data': e['data'],  # Já está no formato BR
                    'valor': float(e['valor'] or 0),
                    'status': e['status'] or 'PENDENTE'
                } for e in entradas],
                'evolucao': [{
                    'data': e['data'],
                    'total': float(e['total'] or 0)
                } for e in evolucao],
                'pizza': pizza,
                'canais': canais
            }

    except Exception as e:
        print(f"Erro ao acessar banco de dados: {str(e)}")
        return {
            'consolidado': {'recebido': 0, 'pendente': 0, 'ml': 0, 'shopee': 0, 'hoje': 0},
            'entradas': [],
            'evolucao': [],
            'pizza': {},
            'canais': []
        }

@bp.route('/entradas', methods=['GET'])
def dashboard():
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')
    canal = request.args.get('canal', '')
    status = request.args.get('status', '')
    pedido_id = request.args.get('pedido_id', '')

    data = get_financial_data(
        data_ini=data_ini,
        data_fim=data_fim,
        canal=canal,
        status=status,
        pedido_id=pedido_id
    )

    cards = [
        {'title': 'Entradas Totais', 'value': data['consolidado']['recebido'] + data['consolidado']['pendente'],
         'icon': 'ri-arrow-down-circle-fill'},
        {'title': 'A Receber', 'value': data['consolidado']['pendente'], 'icon': 'ri-hourglass-fill'},
        {'title': 'Mercado Livre', 'value': data['consolidado']['ml'], 'icon': 'ri-store-2-fill'},
        {'title': 'Shopee', 'value': data['consolidado']['shopee'], 'icon': 'ri-shopping-bag-3-fill'},
        {'title': 'Recebido Hoje', 'value': data['consolidado']['hoje'], 'icon': 'ri-calendar-todo-fill'}
    ]

    return render_template(
        'financeiro/entradas.html',
        cards=cards,
        entradas=data['entradas'],
        evolucao=data['evolucao'],
        canais=data['canais'],
        request=request,
        data_ini=data_ini,
        data_fim=data_fim,
        canal_selecionado=canal,
        status_selecionado=status,
        pedido_id=pedido_id
    )

@bp.route('/entradas/dados')
def dados():
    data_ini = request.args.get('data_ini', '')
    data_fim = request.args.get('data_fim', '')
    canal = request.args.get('canal', '')
    status = request.args.get('status', '')
    pedido_id = request.args.get('pedido_id', '')

    # Mapear status para valores do banco
    status_map = {
        'recebido': 'COMPLETED',
        'pendente': 'PENDING'
    }
    status = status_map.get(status.lower(), status)

    data = get_financial_data(
        data_ini=data_ini,
        data_fim=data_fim,
        canal=canal,
        status=status,
        pedido_id=pedido_id
    )

    response = {
        'cards': [
            {'title': 'Entradas Totais', 'value': data['consolidado']['recebido'] + data['consolidado']['pendente'], "icon": "ri-arrow-down-circle-fill"},
            {'title': 'A Receber', 'value': data['consolidado']['pendente'], "icon": "ri-hourglass-fill"},
            {'title': 'Mercado Livre', 'value': data['consolidado']['ml'], "icon": "ri-store-2-fill"},
            {'title': 'Shopee', 'value': data['consolidado']['shopee'], "icon": "ri-shopping-bag-3-fill"},
            {'title': 'Recebido Hoje', 'value': data['consolidado']['hoje'], "icon": "ri-calendar-todo-fill"}
        ],
        'entradas': data['entradas'],
        'evolucao': {
            'labels': [e['data'] for e in data['evolucao']],
            'data': [e['total'] for e in data['evolucao']]
        },
        'pizza': {
            'labels': list(data['pizza'].keys()),
            'data': list(data['pizza'].values())
        }
    }
    return jsonify(response)
