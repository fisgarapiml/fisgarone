from flask import Blueprint, render_template, request
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import locale
import os

# Configuração de localização
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')

# Blueprint configurado corretamente
shopee_bp = Blueprint(
    'shopee_bp',
    __name__,
    template_folder=os.path.join('..', '..', '..', 'templates', 'vendas', 'shopee'),
    static_folder=os.path.join('..', '..', '..', 'static'),
    url_prefix='/modulos/vendas'
)

def calcular_metricas(df, df_original):
    hoje = datetime.today()
    inicio_mes_atual = hoje.replace(day=1)
    inicio_mes_anterior = (inicio_mes_atual - timedelta(days=1)).replace(day=1)
    fim_mes_anterior = inicio_mes_atual - timedelta(days=1)

    df_mes_atual = df[df['data'] >= inicio_mes_atual]
    df_mes_anterior = df_original[
        (df_original['data'] >= inicio_mes_anterior) &
        (df_original['data'] <= fim_mes_anterior)
    ]
    df_equivalente = df_mes_anterior[df_mes_anterior['data'].dt.day <= hoje.day]

    def formatar_moeda(valor):
        return locale.currency(valor, grouping=True, symbol=False)

    def calcular_variacao(atual, anterior):
        return round(((atual - anterior) / anterior) * 100, 2) if anterior else 0

    # Cálculos principais
    fat_atual = float(df_mes_atual['valor_total'].sum())
    fat_anterior = float(df_mes_anterior['valor_total'].sum())
    fat_equivalente = float(df_equivalente['valor_total'].sum())

    unidades_atual = int(df_mes_atual['qtd_comprada'].sum())
    unidades_anterior = int(df_mes_anterior['qtd_comprada'].sum())

    pedidos_atual = int(df_mes_atual['pedido_id'].nunique())
    pedidos_anterior = int(df_mes_anterior['pedido_id'].nunique())

    ticket_atual = fat_atual / pedidos_atual if pedidos_atual else 0
    ticket_anterior = fat_anterior / pedidos_anterior if pedidos_anterior else 0

    # Preparação do resumo CORRIGIDO
    resumo = {
        'faturamento': formatar_moeda(fat_atual),
        'faturamento_anterior': formatar_moeda(fat_anterior),
        'faturamento_dif': calcular_variacao(fat_atual, fat_anterior),
        'faturamento_equivalente_pct': calcular_variacao(fat_atual, fat_equivalente),
        'unidades': unidades_atual,
        'unidades_anterior': unidades_anterior,
        'unidades_dif': calcular_variacao(unidades_atual, unidades_anterior),
        'pedidos': pedidos_atual,
        'pedidos_anterior': pedidos_anterior,
        'pedidos_dif': calcular_variacao(pedidos_atual, pedidos_anterior),
        'ticket_medio': formatar_moeda(ticket_atual),
        'ticket_medio_anterior': formatar_moeda(ticket_anterior),
        'ticket_medio_dif': calcular_variacao(ticket_atual, ticket_anterior),
        'barras_percentuais': {
            'faturamento': min(max(calcular_variacao(fat_atual, fat_anterior) + 100, 0), 100),
            'unidades': min(max(calcular_variacao(unidades_atual, unidades_anterior) + 100, 0), 100),
            'pedidos': min(max(calcular_variacao(pedidos_atual, pedidos_anterior) + 100, 0), 100),
            'ticket': min(max(calcular_variacao(ticket_atual, ticket_anterior) + 100, 0), 100)
        }
    }

    # Dados para gráficos
    vendas_diarias = []
    if not df_mes_atual.empty:
        vendas_diarias = df_mes_atual.groupby(
            df_mes_atual['data'].dt.strftime('%d/%m')
        )['valor_total'].sum().reset_index().rename(
            columns={'data': 'dia', 'valor_total': 'valor'}
        ).to_dict(orient='records')

    top_produtos = []
    if not df_mes_atual.empty:
        top_produtos = df_mes_atual.groupby('SKU')['valor_total'].sum().nlargest(
            10
        ).reset_index().rename(
            columns={'valor_total': 'valor'}
        ).to_dict(orient='records')

    return resumo, vendas_diarias, top_produtos

@shopee_bp.route('/modulos/vendas/shopee', endpoint='dashboard_shopee')
def dashboard():
    try:
        # Obter parâmetros de filtro
        filtro_sku = request.args.get('sku')
        filtro_conta = request.args.get('conta')
        filtro_mes = request.args.get('mes')

        # Conexão com o banco de dados
        con = sqlite3.connect("grupo_fisgar.db")
        df_original = pd.read_sql_query("SELECT * FROM vendas_shopee", con)
        con.close()

        # Processamento dos dados
        df_original['data'] = pd.to_datetime(df_original['data'])
        df = df_original.copy()

        # Listas para filtros
        lista_skus = sorted(df['SKU'].dropna().unique().tolist())
        lista_contas = sorted(df['tipo_conta'].dropna().unique().tolist())
        lista_meses = sorted(df['data'].dt.strftime('%m').unique().tolist())

        # Aplicar filtros
        if filtro_sku:
            df = df[df['SKU'] == filtro_sku]
        if filtro_conta:
            df = df[df['tipo_conta'] == filtro_conta]
        if filtro_mes:
            mes = int(filtro_mes)
            ano = datetime.today().year if mes <= datetime.today().month else datetime.today().year - 1
            inicio = datetime(ano, mes, 1)
            fim = datetime(ano, mes + 1, 1) - timedelta(days=1) if mes < 12 else datetime(ano, 12, 31)
            df = df[(df['data'] >= inicio) & (df['data'] <= fim)]

        # Calcular métricas
        resumo, vendas_diarias, top_produtos = calcular_metricas(df, df_original)

        return render_template(
            'shopee/dashboard.html',
            resumo=resumo,  # Certifique-se que está usando 'resumo' no template, não 'cards_data'
            vendas_diarias=vendas_diarias,
            top_produtos=top_produtos,
            lista_skus=lista_skus,
            lista_contas=lista_contas,
            lista_meses=lista_meses,
            filtro_sku=filtro_sku,
            filtro_conta=filtro_conta,
            filtro_mes=filtro_mes
        )

    except Exception as e:
        print(f"Erro inesperado: {str(e)}")
        return render_template('error.html', message="Erro ao processar os dados"), 500

blueprint = shopee_bp