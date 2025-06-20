from flask import Blueprint, render_template, request
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
import locale
import os
from calendar import monthrange

# Config regional
try:
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')
except locale.Error:
    locale.setlocale(locale.LC_ALL, 'Portuguese_Brazil')

shopee_bp = Blueprint('shopee_bp', __name__)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, '../../../grupo_fisgar.db')


def calcular_metricas(df, df_original, data_inicio=None, data_fim=None):
    import locale
    from datetime import datetime, timedelta
    from calendar import monthrange

    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

    # Garante que as colunas de data são datetime
    df['data'] = pd.to_datetime(df['data'], errors='coerce')
    df_original['data'] = pd.to_datetime(df_original['data'], errors='coerce')

    # Remove linhas com datas inválidas
    df = df.dropna(subset=['data'])
    df_original = df_original.dropna(subset=['data'])

    hoje = datetime.today().date()

    # Se não veio filtro, usa mês atual
    if data_inicio and data_fim:
        inicio = pd.to_datetime(data_inicio).date()
        fim = pd.to_datetime(data_fim).date()
    else:
        inicio = hoje.replace(day=1)
        fim = hoje

    mes_atual = inicio.month
    ano_atual = inicio.year

    if mes_atual == 1:
        mes_anterior = 12
        ano_anterior = ano_atual - 1
    else:
        mes_anterior = mes_atual - 1
        ano_anterior = ano_atual

    inicio_mes_anterior = datetime(ano_anterior, mes_anterior, 1).date()
    fim_mes_anterior = inicio - timedelta(days=1)

    # Filtra os dataframes mantendo como datetime
    df_mes_atual = df[(df['data'].dt.date >= inicio) & (df['data'].dt.date <= fim)].copy()
    df_mes_anterior = df_original[(df_original['data'].dt.date >= inicio_mes_anterior) &
                                  (df_original['data'].dt.date <= fim_mes_anterior)].copy()

    # Vendas diárias
    max_dias = max(
        monthrange(ano_atual, mes_atual)[1],
        monthrange(ano_anterior, mes_anterior)[1]
    )
    vendas_diarias = []
    for dia in range(1, max_dias + 1):
        try:
            data_atual = datetime(ano_atual, mes_atual, dia).date()
        except ValueError:
            data_atual = None
        try:
            data_ant = datetime(ano_anterior, mes_anterior, dia).date()
        except ValueError:
            data_ant = None

        valor_atual = float(
            df_mes_atual[df_mes_atual['data'].dt.date == data_atual]['valor_total'].sum()) if data_atual else 0.0
        valor_anterior = float(
            df_mes_anterior[df_mes_anterior['data'].dt.date == data_ant]['valor_total'].sum()) if data_ant else 0.0
        vendas_diarias.append({
            'dia': f"{dia:02d}",
            'valor': valor_atual,
            'valor_anterior': valor_anterior
        })

    # Top produtos
    skus_top_atual = (
        df_mes_atual.groupby('SKU')['valor_total']
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .index.tolist()
    )
    top_produtos = []
    for sku in skus_top_atual:
        valor_atual = float(df_mes_atual[df_mes_atual['SKU'] == sku]['valor_total'].sum())
        valor_anterior = float(df_mes_anterior[df_mes_anterior['SKU'] == sku]['valor_total'].sum())
        top_produtos.append({
            'SKU': sku,
            'valor': valor_atual,
            'valor_anterior': valor_anterior
        })

    # --- Cálculos dos cards novos ---
    def formatar_moeda(valor):
        try:
            return locale.currency(float(valor), grouping=True, symbol=False)
        except:
            return "0,00"

    def calcular_variacao(atual, anterior):
        return round(((atual - anterior) / anterior * 100), 2) if anterior else 0

    fat_atual = float(df_mes_atual['valor_total'].sum()) if not df_mes_atual.empty else 0.0
    fat_anterior = float(df_mes_anterior['valor_total'].sum()) if not df_mes_anterior.empty else 0.0
    unidades_atual = int(df_mes_atual['qtd_comprada'].sum()) if not df_mes_atual.empty else 0
    unidades_anterior = int(df_mes_anterior['qtd_comprada'].sum()) if not df_mes_anterior.empty else 0
    pedidos_atual = int(df_mes_atual['pedido_id'].nunique()) if not df_mes_atual.empty else 0
    pedidos_anterior = int(df_mes_anterior['pedido_id'].nunique()) if not df_mes_anterior.empty else 0
    ticket_atual = fat_atual / pedidos_atual if pedidos_atual else 0
    ticket_anterior = fat_anterior / pedidos_anterior if pedidos_anterior else 0

    # LUCRO e MARGEM
    lucro_real = float(df_mes_atual['lucro_real'].sum()) if 'lucro_real' in df_mes_atual.columns else 0.0
    lucro_anterior = float(df_mes_anterior['lucro_real'].sum()) if 'lucro_real' in df_mes_anterior.columns else 0.0
    margem_contrib = (lucro_real / fat_atual * 100) if fat_atual > 0 else 0.0
    margem_anterior = (lucro_anterior / fat_anterior * 100) if fat_anterior > 0 else 0.0

    # FRETE Shopee Direta
    total_frete_shopee = float(df_mes_atual['repasse_envio'].sum()) if 'repasse_envio' in df_mes_atual.columns else 0.0
    qtd_envios_shopee = int((df_mes_atual['repasse_envio'] > 0).sum()) if 'repasse_envio' in df_mes_atual.columns else 0

    # Pareto produtos
    produtos = df.groupby('SKU').agg({'valor_total': 'sum'}).reset_index()
    produtos = produtos.sort_values('valor_total', ascending=False)
    total = produtos['valor_total'].sum()
    produtos['acumulado'] = produtos['valor_total'].cumsum() / total * 100 if total > 0 else 0
    produtos['top20'] = produtos['acumulado'] <= 80  # Top 80% do valor
    pareto_produtos = produtos.to_dict('records')

    resumo = {
        'faturamento': formatar_moeda(fat_atual),
        'faturamento_anterior': formatar_moeda(fat_anterior),
        'faturamento_dif': calcular_variacao(fat_atual, fat_anterior),
        'faturamento_equivalente_pct': 0,
        'unidades': unidades_atual,
        'unidades_anterior': unidades_anterior,
        'unidades_dif': calcular_variacao(unidades_atual, unidades_anterior),
        'pedidos': pedidos_atual,
        'pedidos_anterior': pedidos_anterior,
        'pedidos_dif': calcular_variacao(pedidos_atual, pedidos_anterior),
        'ticket_medio': formatar_moeda(ticket_atual),
        'ticket_medio_anterior': formatar_moeda(ticket_anterior),
        'ticket_medio_dif': calcular_variacao(ticket_atual, ticket_anterior),
        'lucro': formatar_moeda(lucro_real),
        'lucro_anterior': formatar_moeda(lucro_anterior),
        'lucro_dif': calcular_variacao(lucro_real, lucro_anterior),
        'margem': f"{margem_contrib:.1f}%",
        'margem_anterior': f"{margem_anterior:.1f}%",
        'frete_shopee_total': formatar_moeda(total_frete_shopee),
        'frete_shopee_qtd': qtd_envios_shopee,
        'barras_percentuais': {
            'faturamento': min(max(calcular_variacao(fat_atual, fat_anterior) + 100, 0), 100),
            'unidades': min(max(calcular_variacao(unidades_atual, unidades_anterior) + 100, 0), 100),
            'pedidos': min(max(calcular_variacao(pedidos_atual, pedidos_anterior) + 100, 0), 100),
            'ticket': min(max(calcular_variacao(ticket_atual, ticket_anterior) + 100, 0), 100)
        }
    }

    return resumo, vendas_diarias, top_produtos, pareto_produtos


@shopee_bp.route('/shopee', endpoint='dashboard_shopee')
def dashboard():
    try:
        con = sqlite3.connect(DB_PATH)
        df_original = pd.read_sql_query("SELECT * FROM vendas_shopee", con)
        con.close()

        # 1. Garante datetime64 (NÃO faça .dt.date em nenhum momento!)
        df_original['data'] = pd.to_datetime(df_original['data'], errors='coerce')

        # 2. Filtros status
        df_original = df_original[
            ~df_original['status_pedido'].isin(['TO_RETURN', 'CANCELLED', 'UNPAID'])
        ].copy()
        df = df_original.copy()

        # 3. Filtros de busca
        filtro_sku = request.args.get('sku')
        filtro_conta = request.args.get('conta')
        filtro_mes = request.args.get('mes')

        if filtro_sku:
            df = df[df['SKU'] == filtro_sku]
        if filtro_conta:
            df = df[df['tipo_conta'] == filtro_conta]
        if filtro_mes:
            mes = int(filtro_mes)
            ano = datetime.today().year if mes <= datetime.today().month else datetime.today().year - 1
            inicio = datetime(ano, mes, 1)
            if mes < 12:
                fim = datetime(ano, mes + 1, 1) - timedelta(days=1)
            else:
                fim = datetime(ano, 12, 31)
            df = df[(df['data'] >= inicio) & (df['data'] <= fim)]

        # 4. Vendas com prejuízo (NÃO mexa na coluna 'data'!)
        vendas_prejuizo_df = df[df['lucro_real'] < 0].copy()
        vendas_prejuizo_df = vendas_prejuizo_df[
            [
                'data', 'SKU', 'nome_item', 'valor_total', 'preco_custo',
                'custo_op_total', 'margem_contribuicao', 'lucro_real',
                'lucro_real_pct', 'sm_contas_reais', 'comissao_unitaria'
            ]
        ]
        vendas_prejuizo = vendas_prejuizo_df.to_dict(orient='records')

        # 5. MÉTRICAS - passar df e df_original ainda como datetime!
        resumo, vendas_diarias, top_produtos, pareto_produtos = calcular_metricas(df, df_original)

        return render_template(
            'shopee/dashboard.html',
            resumo=resumo,
            vendas_diarias=vendas_diarias,
            top_produtos=top_produtos,
            pareto_produtos=pareto_produtos,
            lista_skus=sorted(df['SKU'].dropna().unique().tolist()),
            lista_contas=sorted(df['tipo_conta'].dropna().unique().tolist()),
            lista_meses=sorted(df['data'].dt.strftime('%m').unique().tolist()),
            filtro_sku=filtro_sku,
            filtro_conta=filtro_conta,
            filtro_mes=filtro_mes,
            vendas_prejuizo=vendas_prejuizo
        )
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")
        return render_template('error.html', message="Erro ao processar os dados"), 500


blueprint = shopee_bp