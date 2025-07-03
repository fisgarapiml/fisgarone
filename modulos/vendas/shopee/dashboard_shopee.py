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
DB_PATH = r'C:\grupo\grupo_fisgar.db'


def calcular_metricas(df, df_original, data_inicio=None, data_fim=None):
    # Converter colunas de data
    df['DATA'] = pd.to_datetime(df['DATA'], errors='coerce')
    df_original['DATA'] = pd.to_datetime(df_original['DATA'], errors='coerce')

    # Remover linhas com datas inválidas
    df = df.dropna(subset=['DATA'])
    df_original = df_original.dropna(subset=['DATA'])

    # Garantir que estamos usando o mesmo ano
    ano = df['DATA'].dt.year.max() if not df.empty else datetime.now().year

    # Definir períodos
    if data_inicio and data_fim:
        inicio = pd.to_datetime(data_inicio).date()
        fim = pd.to_datetime(data_fim).date()
    else:
        if not df.empty:
            inicio = df['DATA'].min().date()
            fim = df['DATA'].max().date()
        else:
            inicio = datetime.now().date().replace(day=1)
            fim = datetime.now().date()

    mes_atual = inicio.month
    ano_atual = ano

    # Mês anterior (dentro do mesmo ano)
    mes_anterior = mes_atual - 1 if mes_atual > 1 else 12
    ano_anterior = ano_atual if mes_atual > 1 else ano_atual - 1

    # Filtrar dados
    df_mes_atual = df.copy()  # Já está filtrado pelo mês

    # Filtrar mês anterior do mesmo ano
    df_mes_anterior = df_original[
        (df_original['DATA'].dt.month == mes_anterior) &
        (df_original['DATA'].dt.year == ano_anterior)
        ].copy()

    # DEBUG
    print(f"\nDEBUG METRICAS:")
    print(f"Mês atual: {mes_atual}/{ano_atual} - Registros: {len(df_mes_atual)}")
    print(f"Mês anterior: {mes_anterior}/{ano_anterior} - Registros: {len(df_mes_anterior)}")


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
            df_mes_atual[df_mes_atual['DATA'].dt.date == data_atual]['VALOR_TOTAL'].sum()) if data_atual else 0.0
        valor_anterior = float(
            df_mes_anterior[df_mes_anterior['DATA'].dt.date == data_ant]['VALOR_TOTAL'].sum()) if data_ant else 0.0
        vendas_diarias.append({
            'dia': f"{dia:02d}",
            'valor': valor_atual,
            'valor_anterior': valor_anterior
        })

    # Top produtos
    skus_top_atual = (
        df_mes_atual.groupby('SKU')['VALOR_TOTAL']
        .sum()
        .sort_values(ascending=False)
        .head(10)
        .index.tolist()
    )
    top_produtos = []
    for sku in skus_top_atual:
        valor_atual = float(df_mes_atual[df_mes_atual['SKU'] == sku]['VALOR_TOTAL'].sum())
        valor_anterior = float(df_mes_anterior[df_mes_anterior['SKU'] == sku]['VALOR_TOTAL'].sum())
        top_produtos.append({
            'SKU': sku,
            'valor': valor_atual,
            'valor_anterior': valor_anterior
        })

    # Cálculos dos cards
    def formatar_moeda(valor):
        try:
            return locale.currency(float(valor), grouping=True, symbol=False)
        except:
            return "0,00"

    def calcular_variacao(atual, anterior):
        return round(((atual - anterior) / anterior * 100), 2) if anterior else 0

    fat_atual = float(df_mes_atual['VALOR_TOTAL'].sum()) if not df_mes_atual.empty else 0.0
    fat_anterior = float(df_mes_anterior['VALOR_TOTAL'].sum()) if not df_mes_anterior.empty else 0.0
    unidades_atual = int(df_mes_atual['QTD_COMPRADA'].sum()) if not df_mes_atual.empty else 0
    unidades_anterior = int(df_mes_anterior['QTD_COMPRADA'].sum()) if not df_mes_anterior.empty else 0
    pedidos_atual = int(df_mes_atual['PEDIDO_ID'].nunique()) if not df_mes_atual.empty else 0
    pedidos_anterior = int(df_mes_anterior['PEDIDO_ID'].nunique()) if not df_mes_anterior.empty else 0
    ticket_atual = fat_atual / pedidos_atual if pedidos_atual else 0
    ticket_anterior = fat_anterior / pedidos_anterior if pedidos_anterior else 0

    # Lucro e Margem
    lucro_real = float(df_mes_atual['LUCRO_REAL'].sum()) if 'LUCRO_REAL' in df_mes_atual.columns else 0.0
    lucro_anterior = float(df_mes_anterior['LUCRO_REAL'].sum()) if 'LUCRO_REAL' in df_mes_anterior.columns else 0.0
    margem_contrib = (lucro_real / fat_atual * 100) if fat_atual > 0 else 0.0
    margem_anterior = (lucro_anterior / fat_anterior * 100) if fat_anterior > 0 else 0.0

    # Frete Shopee
    total_frete_shopee = float(df_mes_atual['REPASSE_ENVIO'].sum()) if 'REPASSE_ENVIO' in df_mes_atual.columns else 0.0
    qtd_envios_shopee = int((df_mes_atual['REPASSE_ENVIO'] > 0).sum()) if 'REPASSE_ENVIO' in df_mes_atual.columns else 0

    # Pareto produtos
    produtos = df.groupby('SKU').agg({'VALOR_TOTAL': 'sum'}).reset_index()
    produtos = produtos.sort_values('VALOR_TOTAL', ascending=False)
    total = produtos['VALOR_TOTAL'].sum()
    produtos['acumulado'] = produtos['VALOR_TOTAL'].cumsum() / total * 100 if total > 0 else 0
    produtos['top20'] = produtos['acumulado'] <= 80
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
        'lucro_var': calcular_variacao(lucro_real, lucro_anterior),
        'margem': f"{margem_contrib:.1f}%",
        'margem_anterior': f"{margem_anterior:.1f}%",
        'margem_var': calcular_variacao(margem_contrib, margem_anterior),
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

        # Converter coluna DATA para datetime
        df_original['DATA'] = pd.to_datetime(df_original['DATA'], errors='coerce')

        # Filtrar status inválidos
        df_original = df_original[~df_original['STATUS_PEDIDO'].isin(['TO_RETURN', 'CANCELLED', 'UNPAID'])].copy()

        # Obter ano atual
        ano_atual = datetime.now().year

        # Aplicar filtros
        df = df_original.copy()
        filtro_sku = request.args.get('sku')
        filtro_conta = request.args.get('conta')
        filtro_mes = request.args.get('mes')

        if filtro_sku:
            df = df[df['SKU'] == filtro_sku]
        if filtro_conta:
            df = df[df['TIPO_CONTA'] == filtro_conta]

        # FILTRO DE MÊS CORRIGIDO (SOLUÇÃO DEFINITIVA)
        if filtro_mes:
            mes = int(filtro_mes)
            # Primeiro verifica se existem dados para o mês/ano atual
            df_mes_filtrado = df[(df['DATA'].dt.month == mes) & (df['DATA'].dt.year == ano_atual)]

            if len(df_mes_filtrado) == 0:
                # Se não encontrar no ano atual, busca no último ano disponível
                ultimo_ano = df['DATA'].dt.year.max()
                df = df[(df['DATA'].dt.month == mes) & (df['DATA'].dt.year == ultimo_ano)]
                print(f"Usando dados de {mes}/{ultimo_ano} (não encontrado no ano atual)")
            else:
                df = df_mes_filtrado
                print(f"Usando dados de {mes}/{ano_atual}")
        else:
            # Se não especificar mês, mostra o mês atual
            mes = datetime.now().month
            df = df[(df['DATA'].dt.month == mes) & (df['DATA'].dt.year == ano_atual)]

        # DEBUG CRÍTICO
        print("\nDEBUG DADOS FILTRADOS:")
        print(f"Total registros: {len(df)}")
        if len(df) > 0:
            print(f"Período: {df['DATA'].min()} até {df['DATA'].max()}")
        else:
            print("ATENÇÃO: Nenhum registro encontrado para os filtros aplicados!")
            print("Verifique se existem dados no banco para:")
            print(f"- Mês: {filtro_mes if filtro_mes else mes}")
            print(f"- Ano: {ano_atual}")

        # Restante do processamento...
        vendas_prejuizo = df[df['LUCRO_REAL'] < 0].to_dict('records')
        resumo, vendas_diarias, top_produtos, pareto_produtos = calcular_metricas(df, df_original)

        return render_template(
            'shopee/dashboard.html',
            resumo=resumo,
            vendas_diarias=vendas_diarias,
            top_produtos=top_produtos,
            pareto_produtos=pareto_produtos,
            lista_skus=sorted(df['SKU'].dropna().unique().tolist()),
            lista_contas=sorted(df['TIPO_CONTA'].dropna().unique().tolist()),
            lista_meses=sorted(df_original['DATA'].dt.strftime('%m').unique().tolist()),
            filtro_sku=filtro_sku,
            filtro_conta=filtro_conta,
            filtro_mes=filtro_mes,
            vendas_prejuizo=vendas_prejuizo
        )
    except Exception as e:
        print(f"Erro inesperado: {str(e)}")
        return render_template('error.html', message="Erro ao processar os dados"), 500

blueprint = shopee_bp