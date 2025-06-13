# raiz/modulos/vendas/shopee/dashboard_shopee.py

from flask import Blueprint, jsonify, request, \
    current_app  # Importe current_app para acessar as configurações da aplicação
import sqlite3
from datetime import datetime, timedelta

# Cria um Blueprint para as rotas do dashboard Shopee
# O nome do blueprint (primeiro argumento) deve ser único na aplicação
shopee_dashboard_bp = Blueprint('shopee_dashboard', __name__)


# --- Funções Auxiliares (mantidas no blueprint para encapsulamento) ---

def parse_period_dates(period, start_date_str, end_date_str):
    """
    Analisa os parâmetros de período e retorna as datas de início e fim.
    Retorna (datetime_start, datetime_end).
    """
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_today = datetime.now()  # Inclui a hora atual para 'today', '7_days', etc.

    if period == 'today':
        start_date = today
        end_date = end_of_today
    elif period == 'yesterday':
        start_date = today - timedelta(days=1)
        end_date = today - timedelta(microseconds=1)  # Fim do dia anterior
    elif period == '7_days':
        start_date = today - timedelta(days=6)  # Últimos 7 dias, incluindo hoje
        end_date = end_of_today
    elif period == '30_days':
        start_date = today - timedelta(days=29)  # Últimos 30 dias, incluindo hoje
        end_date = end_of_today
    elif period == 'current_month':
        start_date = today.replace(day=1)
        end_date = end_of_today
    elif period == 'last_month':
        first_day_current_month = today.replace(day=1)
        start_date = (first_day_current_month - timedelta(days=1)).replace(day=1)
        end_date = first_day_current_month - timedelta(microseconds=1)
    elif period == 'custom' and start_date_str and end_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
            # Garante que a data final inclua o dia inteiro até o último microssegundo
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d') + timedelta(days=1) - timedelta(microseconds=1)
        except ValueError:
            return None, None  # Datas inválidas
    else:
        # Padrão: últimos 30 dias se nenhum período válido for fornecido
        start_date = today - timedelta(days=29)
        end_date = end_of_today

    return start_date, end_date


# --- Rotas da API para o Dashboard Shopee ---

@shopee_dashboard_bp.route('/api/sales/summary', methods=['GET'])
def get_sales_summary():
    """
    Retorna um resumo dos KPIs de vendas para um período especificado.
    Baseado nas colunas: valor_total, pedido_id, lucro_real.
    Inclui comparativo com o período anterior.
    """
    period = request.args.get('period', '30_days')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    current_start, current_end = parse_period_dates(period, start_date_str, end_date_str)
    if current_start is None or current_end is None:
        return jsonify({'error': 'Datas de período personalizadas inválidas.'}), 400

    conn = current_app.get_db()  # Obtém a conexão do DB gerenciada pelo app_central
    cursor = conn.cursor()

    # --- Consulta para o período atual ---
    cursor.execute(f"""
        SELECT
            SUM(valor_total) AS total_sales,
            COUNT(DISTINCT pedido_id) AS num_orders,
            SUM(lucro_real) AS total_real_profit
        FROM vendas_shopee
        WHERE data BETWEEN '{current_start.strftime('%Y-%m-%d %H:%M:%S')}' AND '{current_end.strftime('%Y-%m-%d %H:%M:%S')}'
        AND status_pedido = 'Concluído' -- Considera apenas vendas concluídas para KPIs financeiros
    """)
    current_data = cursor.fetchone()

    total_sales = current_data['total_sales'] if current_data['total_sales'] is not None else 0.0
    num_orders = current_data['num_orders'] if current_data['num_orders'] is not None else 0
    total_real_profit = current_data['total_real_profit'] if current_data['total_real_profit'] is not None else 0.0

    average_ticket = round(total_sales / num_orders, 2) if num_orders > 0 else 0.0
    net_revenue = round(total_real_profit, 2)  # Lucro Real é a "receita líquida" neste contexto

    # --- Consulta para o período anterior (comparativo) ---
    duration = current_end - current_start
    prev_end = current_start - timedelta(microseconds=1)
    prev_start = prev_end - duration

    cursor.execute(f"""
        SELECT
            SUM(valor_total) AS total_sales,
            COUNT(DISTINCT pedido_id) AS num_orders
        FROM vendas_shopee
        WHERE data BETWEEN '{prev_start.strftime('%Y-%m-%d %H:%M:%S')}' AND '{prev_end.strftime('%Y-%m-%d %H:%M:%S')}'
        AND status_pedido = 'Concluído'
    """)
    prev_data = cursor.fetchone()

    total_sales_prev = prev_data['total_sales'] if prev_data['total_sales'] is not None else 0.0
    num_orders_prev = prev_data['num_orders'] if prev_data['num_orders'] is not None else 0

    sales_change_percent = round(((total_sales - total_sales_prev) / total_sales_prev) * 100,
                                 2) if total_sales_prev > 0 else (100 if total_sales > 0 else 0)
    orders_change_percent = round(((num_orders - num_orders_prev) / num_orders_prev) * 100,
                                  2) if num_orders_prev > 0 else (100 if num_orders > 0 else 0)

    return jsonify({
        'total_sales': total_sales,
        'num_orders': num_orders,
        'average_ticket': average_ticket,
        'net_revenue': net_revenue,
        'comparative_data': {
            'sales_change_percent': sales_change_percent,
            'orders_change_percent': orders_change_percent,
            'prev_period_sales': total_sales_prev,
            'prev_period_orders': num_orders_prev
        }
    })


@shopee_dashboard_bp.route('/api/sales/products', methods=['GET'])
def get_top_products():
    """
    Retorna os produtos mais vendidos para um período, baseado em 'nome_item' e 'valor_total'.
    """
    period = request.args.get('period', '30_days')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    limit = int(request.args.get('limit', 10))

    start_date, end_date = parse_period_dates(period, start_date_str, end_date_str)
    if start_date is None or end_date is None:
        return jsonify({'error': 'Datas de período personalizadas inválidas.'}), 400

    conn = current_app.get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT
            nome_item,
            SUM(valor_total) AS total_value,
            SUM(qtd_comprada) AS quantity_sold
        FROM vendas_shopee
        WHERE data BETWEEN '{start_date.strftime('%Y-%m-%d %H:%M:%S')}' AND '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
        AND status_pedido = 'Concluído'
        GROUP BY nome_item
        ORDER BY total_value DESC
        LIMIT ?
    """, (limit,))
    products = [dict(row) for row in cursor.fetchall()]
    return jsonify(products)


@shopee_dashboard_bp.route('/api/sales/categories', methods=['GET'])
def get_top_categories():
    """
    Retorna as categorias mais vendidas para um período, baseado no prefixo do 'SKU'.
    Ajuste a lógica SQL se você tiver uma coluna de categoria explícita.
    """
    period = request.args.get('period', '30_days')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    limit = int(request.args.get('limit', 10))

    start_date, end_date = parse_period_dates(period, start_date_str, end_date_str)
    if start_date is None or end_date is None:
        return jsonify({'error': 'Datas de período personalizadas inválidas.'}), 400

    conn = current_app.get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT
            SUBSTR(SKU, 1, INSTR(SKU, '0')-1) AS categoria_produto, -- Extrai a parte da categoria do SKU (ex: 'ELETRO' de 'ELETRO001')
            SUM(valor_total) AS total_value
        FROM vendas_shopee
        WHERE data BETWEEN '{start_date.strftime('%Y-%m-%d %H:%M:%S')}' AND '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
        AND status_pedido = 'Concluído'
        GROUP BY categoria_produto
        ORDER BY total_value DESC
        LIMIT ?
    """, (limit,))
    categories = [dict(row) for row in cursor.fetchall()]
    # Filtra categorias vazias ou nulas que podem surgir de SKUs sem '0'
    categories = [c for c in categories if c['categoria_produto']]
    return jsonify(categories)


@shopee_dashboard_bp.route('/api/sales/time', methods=['GET'])
def get_sales_over_time():
    """
    Retorna as vendas e número de pedidos ao longo do tempo com granularidade diária, semanal ou mensal.
    Baseado nas colunas 'data', 'valor_total' e 'pedido_id'.
    """
    period = request.args.get('period', '30_days')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    granularity = request.args.get('granularity', 'daily')  # 'daily', 'weekly', 'monthly'

    start_date, end_date = parse_period_dates(period, start_date_str, end_date_str)
    if start_date is None or end_date is None:
        return jsonify({'error': 'Datas de período personalizadas inválidas.'}), 400

    conn = current_app.get_db()
    cursor = conn.cursor()

    if granularity == 'daily':
        group_by = "STRFTIME('%Y-%m-%d', data)"
    elif granularity == 'weekly':
        group_by = "STRFTIME('%Y-%W', data)"
    elif granularity == 'monthly':
        group_by = "STRFTIME('%Y-%m', data)"
    else:
        return jsonify({'error': 'Granularidade inválida. Use "daily", "weekly" ou "monthly".'}), 400

    cursor.execute(f"""
        SELECT
            {group_by} AS date,
            SUM(valor_total) AS total_sales,
            COUNT(DISTINCT pedido_id) AS num_orders
        FROM vendas_shopee
        WHERE data BETWEEN '{start_date.strftime('%Y-%m-%d %H:%M:%S')}' AND '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
        AND status_pedido = 'Concluído'
        GROUP BY date
        ORDER BY date ASC
    """)
    sales_data = [dict(row) for row in cursor.fetchall()]
    return jsonify(sales_data)


@shopee_dashboard_bp.route('/api/sales/payment_methods', methods=['GET'])
def get_sales_by_payment_methods():
    """
    Retorna a distribuição de vendas por 'tipo_conta' para um período.
    Se você tiver uma coluna de método de pagamento explícita, ajuste aqui.
    """
    period = request.args.get('period', '30_days')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date, end_date = parse_period_dates(period, start_date_str, end_date_str)
    if start_date is None or end_date is None:
        return jsonify({'error': 'Datas de período personalizadas inválidas.'}), 400

    conn = current_app.get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT
            tipo_conta,
            SUM(valor_total) AS total_value,
            COUNT(DISTINCT pedido_id) AS num_orders
        FROM vendas_shopee
        WHERE data BETWEEN '{start_date.strftime('%Y-%m-%d %H:%M:%S')}' AND '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
        AND status_pedido = 'Concluído'
        GROUP BY tipo_conta
        ORDER BY total_value DESC
    """)
    payment_methods_data = [dict(row) for row in cursor.fetchall()]
    return jsonify(payment_methods_data)


@shopee_dashboard_bp.route('/api/sales/status', methods=['GET'])
def get_sales_by_status():
    """
    Retorna a contagem de vendas por 'status_pedido' para um período.
    """
    period = request.args.get('period', '30_days')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date, end_date = parse_period_dates(period, start_date_str, end_date_str)
    if start_date is None or end_date is None:
        return jsonify({'error': 'Datas de período personalizadas inválidas.'}), 400

    conn = current_app.get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT
            status_pedido,
            COUNT(DISTINCT pedido_id) AS num_orders,
            SUM(valor_total) AS total_value
        FROM vendas_shopee
        WHERE data BETWEEN '{start_date.strftime('%Y-%m-%d %H:%M:%S')}' AND '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
        GROUP BY status_pedido
        ORDER BY num_orders DESC
    """)
    sales_status_data = [dict(row) for row in cursor.fetchall()]
    return jsonify(sales_status_data)


@shopee_dashboard_bp.route('/api/sales/region', methods=['GET'])
def get_sales_by_region():
    """
    Retorna as vendas por 'transportadora' para um período.
    Se você tiver uma coluna de estado/cidade explícita para o comprador, ajuste aqui.
    """
    period = request.args.get('period', '30_days')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    start_date, end_date = parse_period_dates(period, start_date_str, end_date_str)
    if start_date is None or end_date is None:
        return jsonify({'error': 'Datas de período personalizadas inválidas.'}), 400

    conn = current_app.get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT
            transportadora,
            SUM(valor_total) AS total_value,
            COUNT(DISTINCT pedido_id) AS num_orders
        FROM vendas_shopee
        WHERE data BETWEEN '{start_date.strftime('%Y-%m-%d %H:%M:%S')}' AND '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'
        AND status_pedido = 'Concluído'
        GROUP BY transportadora
        ORDER BY total_value DESC
    """)
    region_data = [dict(row) for row in cursor.fetchall()]
    return jsonify(region_data)


@shopee_dashboard_bp.route('/api/sales/recent', methods=['GET'])
def get_recent_sales():
    """
    Retorna uma lista das vendas mais recentes.
    Baseado em 'pedido_id', 'data', 'nome_item', 'valor_total', 'status_pedido'.
    """
    limit = int(request.args.get('limit', 15))  # Padrão: 15 últimas vendas

    conn = current_app.get_db()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT
            pedido_id,
            data,
            nome_item,
            valor_total,
            status_pedido
        FROM vendas_shopee
        ORDER BY data DESC
        LIMIT ?
    """, (limit,))
    recent_sales = [dict(row) for row in cursor.fetchall()]
    return jsonify(recent_sales)

