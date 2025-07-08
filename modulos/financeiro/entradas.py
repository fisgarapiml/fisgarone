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

def calcula_liquido(row):
    try:
        if row['valor_liquido'] is not None:
            return float(row['valor_liquido'])
        return float(row['valor_total'] or 0) - float(row['comissoes'] or 0) - float(row['taxas'] or 0)
    except Exception:
        return 0.0

def format_data_br(data_str):
    # Converte de 'YYYY-MM-DD' ou 'YYYY-MM-DD HH:MM:SS' para 'DD/MM/YYYY'
    if not data_str:
        return ''
    try:
        if '/' in data_str:  # Já está no formato brasileiro
            return data_str.split()[0]
        return datetime.strptime(data_str.split()[0], '%Y-%m-%d').strftime('%d/%m/%Y')
    except Exception:
        return data_str

def get_financial_data(data_ini='', data_fim='', canal='', status='', pedido_id=''):
    where = []
    params = []

    # Filtros convertidos para padrão do banco (BR)
    if data_ini:
        try:
            data_ini_fmt = datetime.strptime(data_ini, '%d/%m/%Y').strftime('%Y-%m-%d')
            where.append("substr(data_liberacao,7,4)||'-'||substr(data_liberacao,4,2)||'-'||substr(data_liberacao,1,2) >= ?")
            params.append(data_ini_fmt)
        except:
            pass
    if data_fim:
        try:
            data_fim_fmt = datetime.strptime(data_fim, '%d/%m/%Y').strftime('%Y-%m-%d')
            where.append("substr(data_liberacao,7,4)||'-'||substr(data_liberacao,4,2)||'-'||substr(data_liberacao,1,2) <= ?")
            params.append(data_fim_fmt)
        except:
            pass
    if canal:
        where.append("LOWER(tipo) LIKE ?")
        params.append(f"%{canal.lower()}%")
    if status:
        where.append("LOWER(status) = ?")
        params.append(status.lower())
    if pedido_id:
        where.append("pedido_id LIKE ?")
        params.append(f"%{pedido_id}%")

    where_clause = f"WHERE {' AND '.join(where)}" if where else ""

    try:
        with get_db_connection() as conn:
            # Consolidado dos cards
            cons_query = f"""
                SELECT
                    COALESCE(SUM(CASE WHEN status = 'COMPLETED' THEN valor_liquido ELSE 0 END),0) as recebidas,
                    COALESCE(SUM(CASE WHEN status != 'COMPLETED' OR status IS NULL THEN valor_liquido ELSE 0 END),0) as pendentes,
                    COALESCE(SUM(CASE WHEN LOWER(tipo) = 'ml' AND status = 'COMPLETED' THEN valor_liquido ELSE 0 END),0) as ml,
                    COALESCE(SUM(CASE WHEN LOWER(tipo) = 'shopee' AND status = 'COMPLETED' THEN valor_liquido ELSE 0 END),0) as shopee,
                    COALESCE(SUM(CASE WHEN date(substr(data_liberacao,7,4)||'-'||substr(data_liberacao,4,2)||'-'||substr(data_liberacao,1,2)) = date('now') AND status = 'COMPLETED' THEN valor_liquido ELSE 0 END),0) as hoje
                FROM entradas_financeiras
                {where_clause}
            """
            consolidado = conn.execute(cons_query, params).fetchone()

            # Últimas 7 entradas (qualquer status)
            entradas_query = f"""
                SELECT 
                    pedido_id,
                    tipo as canal,
                    data_liberacao as data,
                    COALESCE(valor_liquido, 0) as valor,
                    status
                FROM entradas_financeiras
                {where_clause}
                ORDER BY substr(data_liberacao,7,4)||'-'||substr(data_liberacao,4,2)||'-'||substr(data_liberacao,1,2) DESC
                LIMIT 7
            """
            entradas = conn.execute(entradas_query, params).fetchall()

            # Evolução diária (recebidas)
            evolucao_query = f"""
                SELECT 
                    data_liberacao as data,
                    SUM(COALESCE(valor_liquido, 0)) as total
                FROM entradas_financeiras
                WHERE status = 'COMPLETED'
                {"AND " + " AND ".join(where) if where else ""}
                GROUP BY data_liberacao
                ORDER BY substr(data_liberacao,7,4)||'-'||substr(data_liberacao,4,2)||'-'||substr(data_liberacao,1,2)
            """
            evolucao = conn.execute(evolucao_query, params).fetchall()

            # Pizza: total por canal
            pizza_query = f"""
                SELECT tipo as canal, SUM(COALESCE(valor_liquido, 0)) as total
                FROM entradas_financeiras
                WHERE status = 'COMPLETED'
                {f'AND ' + ' AND '.join(where) if where else ''}
                GROUP BY canal
            """
            pizza_result = conn.execute(pizza_query, params).fetchall()
            pizza = {row['canal']: float(row['total'] or 0) for row in pizza_result if row['canal']}

            cons = {
                'recebido': float(consolidado['recebidas'] or 0),
                'pendente': float(consolidado['pendentes'] or 0),
                'ml': float(consolidado['ml'] or 0),
                'shopee': float(consolidado['shopee'] or 0),
                'hoje': float(consolidado['hoje'] or 0)
            }

            entradas_list = []
            for e in entradas:
                data_br = format_data_br(e['data'])
                entradas_list.append({
                    'pedido_id': e['pedido_id'],
                    'canal': e['canal'],
                    'data': data_br,
                    'valor': float(e['valor'] or 0),
                    'status': e['status'] or '',
                })

            evolucao_list = []
            for e in evolucao:
                evolucao_list.append({
                    'data': format_data_br(e['data']),
                    'total': float(e['total'] or 0)
                })

            canais_list = []
            canais_raw = conn.execute("SELECT DISTINCT tipo FROM entradas_financeiras").fetchall()
            canais_list = [row['tipo'] for row in canais_raw if row['tipo']]

            return {
                'consolidado': cons,
                'entradas': entradas_list,
                'evolucao': evolucao_list,
                'canais': canais_list,
                'pizza': pizza
            }
    except Exception as e:
        print(f"Erro ao acessar banco de dados: {str(e)}")
        return empty_response()

# --------- ROTAS -----------

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
        {'title': 'Entradas Totais', 'value': data['consolidado']['recebido'] + data['consolidado']['pendente'], 'icon': 'ri-money-dollar-circle-fill'},
        {'title': 'A Receber', 'value': data['consolidado']['pendente'], 'icon': 'ri-time-line'},
        {'title': 'Mercado Livre', 'value': data['consolidado']['ml'], 'icon': 'ri-shopping-bag-3-fill'},
        {'title': 'Shopee', 'value': data['consolidado']['shopee'], 'icon': 'ri-store-2-fill'},
        {'title': 'Recebido Hoje', 'value': data['consolidado']['hoje'], 'icon': 'ri-calendar-check-fill'}
    ]
    return render_template(
        'financeiro/entradas.html',
        cards=cards,
        entradas=data['entradas'],
        evolucao=data['evolucao'],
        canais=data['canais'],
        request=request
    )

@bp.route('/entradas/dados')
def dados():
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

    labels = [x['data'] for x in data['evolucao']]
    valores = [x['total'] for x in data['evolucao']]
    pizza_labels = [str(k).title() for k in data['pizza'].keys()]
    pizza_data = [v for v in data['pizza'].values()]

    return jsonify({
        'consolidado': data['consolidado'],
        'entradas': data['entradas'],
        'evolucao': {
            'labels': labels,
            'data': valores
        },
        'pizza': {
            'labels': pizza_labels,
            'data': pizza_data
        }
    })
