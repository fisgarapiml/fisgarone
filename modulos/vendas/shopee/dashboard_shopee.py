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
DB_PATH = r'C:\fisgarone\fisgarone.db'


def calcular_metricas(df, df_original, data_inicio=None, data_fim=None):
    # Configuração inicial
    locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

    # Converter e validar datas
    df = df.copy()
    df_original = df_original.copy()

    for frame in [df, df_original]:
        frame['DATA'] = pd.to_datetime(frame['DATA'], errors='coerce')
        frame.dropna(subset=['DATA'], inplace=True)

    # Determinar período de análise
    if data_inicio and data_fim:
        inicio = pd.to_datetime(data_inicio).date()
        fim = pd.to_datetime(data_fim).date()
    else:
        inicio = df['DATA'].min().date() if not df.empty else datetime.now().date().replace(day=1)
        fim = df['DATA'].max().date() if not df.empty else datetime.now().date()

    mes_atual = inicio.month
    ano_atual = inicio.year

    # Mês anterior (ajuste para ano anterior se necessário)
    mes_anterior = mes_atual - 1 if mes_atual > 1 else 12
    ano_anterior = ano_atual if mes_atual > 1 else ano_atual - 1

    # Filtrar dados
    df_mes_atual = df[(df['DATA'].dt.date >= inicio) & (df['DATA'].dt.date <= fim)].copy()
    df_mes_anterior = df_original[
        (df_original['DATA'].dt.month == mes_anterior) &
        (df_original['DATA'].dt.year == ano_anterior)
        ].copy()

    # DEBUG
    print(f"\nDEBUG METRICAS:")
    print(f"Período atual: {inicio} a {fim} - Registros: {len(df_mes_atual)}")
    print(f"Mês anterior: {mes_anterior}/{ano_anterior} - Registros: {len(df_mes_anterior)}")

    # Helper functions
    def safe_divide(a, b):
        return a / b if b != 0 else 0

    def formatar_moeda(valor):
        try:
            return locale.currency(float(valor), grouping=True, symbol=False)
        except:
            return "0,00"

    def calcular_variacao(atual, anterior):
        return round(safe_divide((atual - anterior), anterior) * 100, 2) if anterior != 0 else 0

    # Cálculo de métricas básicas
    fat_atual = df_mes_atual['VALOR_TOTAL'].sum()
    fat_anterior = df_mes_anterior['VALOR_TOTAL'].sum()

    unidades_atual = df_mes_atual['QTD_COMPRADA'].sum()
    unidades_anterior = df_mes_anterior['QTD_COMPRADA'].sum()

    pedidos_atual = df_mes_atual['PEDIDO_ID'].nunique()
    pedidos_anterior = df_mes_anterior['PEDIDO_ID'].nunique()

    ticket_atual = safe_divide(fat_atual, pedidos_atual)
    ticket_anterior = safe_divide(fat_anterior, pedidos_anterior)

    # Cálculo de lucro e margem (se existirem as colunas)
    lucro_real = df_mes_atual['LUCRO_REAL'].sum() if 'LUCRO_REAL' in df_mes_atual.columns else 0
    lucro_anterior = df_mes_anterior['LUCRO_REAL'].sum() if 'LUCRO_REAL' in df_mes_anterior.columns else 0
    margem_contrib = safe_divide(lucro_real, fat_atual) * 100
    margem_anterior = safe_divide(lucro_anterior, fat_anterior) * 100

    # Frete Shopee (se existir a coluna)
    total_frete_shopee = df_mes_atual['REPASSE_ENVIO'].sum() if 'REPASSE_ENVIO' in df_mes_atual.columns else 0
    qtd_envios_shopee = (df_mes_atual['REPASSE_ENVIO'] > 0).sum() if 'REPASSE_ENVIO' in df_mes_atual.columns else 0

    # Vendas diárias
    max_dias = max(monthrange(ano_atual, mes_atual)[1], monthrange(ano_anterior, mes_anterior)[1])
    vendas_diarias = []

    for dia in range(1, max_dias + 1):
        try:
            data_atual = datetime(ano_atual, mes_atual, dia).date()
            valor_atual = df_mes_atual[df_mes_atual['DATA'].dt.date == data_atual]['VALOR_TOTAL'].sum()
        except:
            data_atual = None
            valor_atual = 0

        try:
            data_ant = datetime(ano_anterior, mes_anterior, dia).date()
            valor_anterior = df_mes_anterior[df_mes_anterior['DATA'].dt.date == data_ant]['VALOR_TOTAL'].sum()
        except:
            data_ant = None
            valor_anterior = 0

        vendas_diarias.append({
            'dia': f"{dia:02d}",
            'valor': float(valor_atual),
            'valor_anterior': float(valor_anterior)
        })

    # Top produtos
    top_produtos = []
    skus_top = df_mes_atual.groupby('SKU')['VALOR_TOTAL'].sum().nlargest(10).index

    for sku in skus_top:
        valor_atual = df_mes_atual[df_mes_atual['SKU'] == sku]['VALOR_TOTAL'].sum()
        valor_anterior = df_mes_anterior[df_mes_anterior['SKU'] == sku]['VALOR_TOTAL'].sum()
        top_produtos.append({
            'SKU': sku,
            'valor': float(valor_atual),
            'valor_anterior': float(valor_anterior)
        })

    # Análise de Pareto (80/20) - VERSÃO CORRIGIDA
    def calcular_pareto(df):
        """Calcula os dados para o gráfico Pareto 80/20"""
        if df.empty:
            return pd.DataFrame(columns=['SKU', 'VALOR_TOTAL', 'percentual', 'acumulado', 'e_top20'])

        # Agrupa por SKU e soma os valores
        pareto_data = df.groupby('SKU', as_index=False).agg({
            'VALOR_TOTAL': 'sum'
        }).sort_values('VALOR_TOTAL', ascending=False)

        # Remove produtos com valor zero
        pareto_data = pareto_data[pareto_data['VALOR_TOTAL'] > 0]

        if pareto_data.empty:
            return pd.DataFrame(columns=['SKU', 'VALOR_TOTAL', 'percentual', 'acumulado', 'e_top20'])

        # Calcula percentuais
        total_vendas = pareto_data['VALOR_TOTAL'].sum()
        pareto_data['percentual'] = (pareto_data['VALOR_TOTAL'] / total_vendas) * 100
        pareto_data['acumulado'] = pareto_data['percentual'].cumsum()

        # Identifica os produtos que compõem 80% do faturamento
        pareto_data['e_top20'] = pareto_data['acumulado'] <= 80

        # Adiciona linha de referência dos 80%
        linha_80 = pd.DataFrame({
            'SKU': ['80% Referência'],
            'VALOR_TOTAL': [0],
            'percentual': [0],
            'acumulado': [80],
            'e_top20': [False]
        })

        return pd.concat([pareto_data, linha_80], ignore_index=True)

    # Aplicar a função ao DataFrame
    pareto_data = calcular_pareto(df_mes_atual)
    pareto_produtos = pareto_data.to_dict('records')

    # DEBUG - Verificar dados do Pareto
    print("\nDEBUG PARETO:")
    print(pareto_data.head())
    if not pareto_data.empty:
        print(f"Total produtos: {len(pareto_data)}")
        print(f"Produtos no top 20%: {pareto_data['e_top20'].sum()}")
        print(f"Valor acumulado máximo: {pareto_data['acumulado'].max():.2f}%")
    else:
        print("ATENÇÃO: Nenhum dado válido para o gráfico Pareto!")

    # Preparar resultado final
    resumo = {
        'faturamento': formatar_moeda(fat_atual),
        'faturamento_anterior': formatar_moeda(fat_anterior),
        'faturamento_dif': calcular_variacao(fat_atual, fat_anterior),
        'unidades': int(unidades_atual),
        'unidades_anterior': int(unidades_anterior),
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
        'margem_var': calcular_variacao(margem_contrib, margem_anterior),
        'frete_shopee_total': formatar_moeda(total_frete_shopee),
        'frete_shopee_qtd': int(qtd_envios_shopee),
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
            'vendas/shopee/dashboard.html',
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
        return render_template('vendas/shopee/error.html', message="Erro ao processar os dados"), 500

blueprint = shopee_bp