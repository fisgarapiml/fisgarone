from flask import Blueprint, render_template, request
import sqlite3
import pandas as pd

ml_bp = Blueprint(
    'ml_bp',
    __name__,
    template_folder='../../templates/vendas'
)

# Tradução dos status do banco para exibição
STATUS_LABELS = {
    'paid': 'Pago',
    'cancelled': 'Cancelado',
    'pending': 'Pendente',
    'shipped': 'Enviado',
    'delivered': 'Entregue',
    'ready_to_ship': 'Pronto para Envio',
    # Complete conforme precisar
}

def get_db_connection():
    conn = sqlite3.connect('grupo_fisgar.db')
    conn.row_factory = sqlite3.Row
    return conn

@ml_bp.route('/vendas-ml')
def dashboard_vendas_ml():
    conn = get_db_connection()
    df = pd.read_sql_query("SELECT * FROM vendas_ml", conn)
    conn.close()

    # Filtros
    mes = request.args.get('mes')
    status = request.args.get('status')
    if mes:
        df = df[df['date_created'].str[:7] == mes]
    if status:
        df = df[df['status'] == status]

    # KPIs
    faturamento = float((df['unit_price'] * df['quantity']).sum())
    unidades = int(df['quantity'].sum())
    pedidos = df.shape[0]
    ticket_medio = faturamento / pedidos if pedidos > 0 else 0

    # Top 10 SKUs vendidos
    top10 = df.groupby('sku').agg({'quantity': 'sum'}).sort_values('quantity', ascending=False).head(10).reset_index()

    # Tradução para filtro
    statuses = sorted(df['status'].dropna().unique())
    status_options = [(s, STATUS_LABELS.get(s, s.capitalize())) for s in statuses]

    # Para o gráfico de status, já traduzido
    status_contagem_raw = df['status'].value_counts().to_dict()
    status_contagem = {STATUS_LABELS.get(k, k.capitalize()): v for k, v in status_contagem_raw.items()}

    # Vendas diárias
    df['dia'] = df['date_created'].str[8:10]
    vendas_dia = df.groupby('dia').agg({'quantity': 'sum'}).reset_index()

    # Meses disponíveis
    meses = sorted(df['date_created'].dropna().apply(lambda x: x[:7]).unique(), reverse=True)

    return render_template(
        'vendas/vendas_ml_dashboard.html',
        faturamento=faturamento,
        unidades=unidades,
        pedidos=pedidos,
        ticket_medio=ticket_medio,
        top10=top10,
        status_options=status_options,
        status_contagem=status_contagem,
        vendas_dia=vendas_dia,
        meses=meses,
        mes_select=mes,
        status_select=status
    )
