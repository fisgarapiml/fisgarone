from flask import Blueprint, render_template, request, jsonify, current_app
import sqlite3
from datetime import datetime, timedelta
import json

dashboard_finance_bp = Blueprint('dashboard_financeiro', __name__,
                        url_prefix='/financeiro/dashboard_finance',
                        template_folder='templates')

def get_db_connection():
    """Função para obter conexão com o banco de dados"""
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

def format_currency(value):
    """Formatar valor para moeda brasileira"""
    if value is None:
        value = 0
    return f"R$ {abs(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def get_financial_summary():
    """Obter resumo financeiro consolidado"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Data atual para filtros
    hoje = datetime.now()
    mes_atual = f"{hoje.month:02d}/{hoje.year}"
    
    try:
        # Total de entradas do mês atual
        cursor.execute("""
            SELECT COALESCE(SUM(valor_liquido), 0) as total_entradas
            FROM entradas_financeiras 
            WHERE status = 'COMPLETED'
            AND substr(data_liberacao, 4, 7) = ?
        """, (mes_atual,))
        total_entradas = cursor.fetchone()['total_entradas']
        
        # Total de saídas do mês atual
        cursor.execute("""
            SELECT COALESCE(SUM(ABS(valor)), 0) as total_saidas
            FROM contas_a_pagar 
            WHERE substr(vencimento, 4, 7) = ?
        """, (mes_atual,))
        total_saidas = cursor.fetchone()['total_saidas']
        
        # Saldo atual
        saldo_atual = total_entradas - total_saidas
        
        # Contas vencidas
        cursor.execute("""
            SELECT COALESCE(SUM(ABS(valor)), 0) as vencidas
            FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
            AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) < date('now')
        """)
        contas_vencidas = cursor.fetchone()['vencidas']
        
        # Contas a vencer hoje
        cursor.execute("""
            SELECT COALESCE(SUM(ABS(valor)), 0) as hoje
            FROM contas_a_pagar
            WHERE (valor_pago IS NULL OR valor_pago = 0)
            AND date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) = date('now')
        """)
        contas_hoje = cursor.fetchone()['hoje']
        
        # Entradas pendentes
        cursor.execute("""
            SELECT COALESCE(SUM(valor_liquido), 0) as pendentes
            FROM entradas_financeiras 
            WHERE status != 'COMPLETED'
        """)
        entradas_pendentes = cursor.fetchone()['pendentes']
        
        # Entradas do dia
        cursor.execute("""
            SELECT COALESCE(SUM(valor_liquido), 0) as hoje
            FROM entradas_financeiras 
            WHERE status = 'COMPLETED'
            AND date(substr(data_liberacao, 7, 4) || '-' || substr(data_liberacao, 4, 2) || '-' || substr(data_liberacao, 1, 2)) = date('now')
        """)
        entradas_hoje = cursor.fetchone()['hoje']
        
        return {
            'total_entradas': float(total_entradas),
            'total_saidas': float(total_saidas),
            'saldo_atual': float(saldo_atual),
            'contas_vencidas': float(contas_vencidas),
            'contas_hoje': float(contas_hoje),
            'entradas_pendentes': float(entradas_pendentes),
            'entradas_hoje': float(entradas_hoje)
        }
        
    except Exception as e:
        print(f"Erro ao obter resumo financeiro: {e}")
        return {
            'total_entradas': 0,
            'total_saidas': 0,
            'saldo_atual': 0,
            'contas_vencidas': 0,
            'contas_hoje': 0,
            'entradas_pendentes': 0,
            'entradas_hoje': 0
        }
    finally:
        conn.close()

def get_fluxo_caixa_mensal():
    """Obter dados do fluxo de caixa dos últimos 12 meses"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Últimos 12 meses
        meses = []
        hoje = datetime.now()
        
        for i in range(11, -1, -1):
            data = hoje - timedelta(days=30*i)
            mes_ano = f"{data.month:02d}/{data.year}"
            meses.append(mes_ano)
        
        fluxo_data = []
        
        for mes in meses:
            # Entradas do mês
            cursor.execute("""
                SELECT COALESCE(SUM(valor_liquido), 0) as entradas
                FROM entradas_financeiras 
                WHERE status = 'COMPLETED'
                AND substr(data_liberacao, 4, 7) = ?
            """, (mes,))
            entradas = cursor.fetchone()['entradas']
            
            # Saídas do mês
            cursor.execute("""
                SELECT COALESCE(SUM(ABS(valor)), 0) as saidas
                FROM contas_a_pagar 
                WHERE substr(vencimento, 4, 7) = ?
            """, (mes,))
            saidas = cursor.fetchone()['saidas']
            
            fluxo_data.append({
                'mes': mes,
                'entradas': float(entradas),
                'saidas': float(saidas),
                'saldo': float(entradas - saidas)
            })
        
        return fluxo_data
        
    except Exception as e:
        print(f"Erro ao obter fluxo de caixa: {e}")
        return []
    finally:
        conn.close()

def get_categorias_despesas():
    """Obter distribuição de despesas por categoria"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    hoje = datetime.now()
    mes_atual = f"{hoje.month:02d}/{hoje.year}"
    
    try:
        cursor.execute("""
            SELECT categorias, COALESCE(SUM(ABS(valor)), 0) as total
            FROM contas_a_pagar
            WHERE substr(vencimento, 4, 7) = ?
            AND categorias IS NOT NULL AND TRIM(categorias) != ''
            GROUP BY categorias
            HAVING total > 0
            ORDER BY total DESC
        """, (mes_atual,))
        
        return [{'categoria': row['categorias'], 'valor': float(row['total'])} 
                for row in cursor.fetchall()]
        
    except Exception as e:
        print(f"Erro ao obter categorias de despesas: {e}")
        return []
    finally:
        conn.close()

def get_canais_receita():
    """Obter distribuição de receitas por canal"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    hoje = datetime.now()
    mes_atual = f"{hoje.month:02d}/{hoje.year}"
    
    try:
        cursor.execute("""
            SELECT origem_conta, COALESCE(SUM(valor_liquido), 0) as total
            FROM entradas_financeiras
            WHERE status = 'COMPLETED'
            AND substr(data_liberacao, 4, 7) = ?
            AND origem_conta IS NOT NULL AND TRIM(origem_conta) != ''
            GROUP BY origem_conta
            HAVING total > 0
            ORDER BY total DESC
        """, (mes_atual,))
        
        return [{'canal': row['origem_conta'], 'valor': float(row['total'])} 
                for row in cursor.fetchall()]
        
    except Exception as e:
        print(f"Erro ao obter canais de receita: {e}")
        return []
    finally:
        conn.close()

def get_ultimas_transacoes():
    """Obter as últimas transações (entradas e saídas)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Últimas entradas
        cursor.execute("""
            SELECT 'entrada' as tipo, pedido_id as descricao, data_liberacao as data, 
                   valor_liquido as valor, origem_conta as detalhes
            FROM entradas_financeiras
            WHERE status = 'COMPLETED'
            ORDER BY date(substr(data_liberacao, 7, 4) || '-' || substr(data_liberacao, 4, 2) || '-' || substr(data_liberacao, 1, 2)) DESC
            LIMIT 10
        """)
        entradas = cursor.fetchall()
        
        # Últimas saídas
        cursor.execute("""
            SELECT 'saida' as tipo, fornecedor as descricao, vencimento as data, 
                   valor, categorias as detalhes
            FROM contas_a_pagar
            WHERE valor_pago > 0
            ORDER BY date(substr(vencimento, 7, 4) || '-' || substr(vencimento, 4, 2) || '-' || substr(vencimento, 1, 2)) DESC
            LIMIT 10
        """)
        saidas = cursor.fetchall()
        
        # Combinar e ordenar
        transacoes = []
        
        for entrada in entradas:
            transacoes.append({
                'tipo': 'entrada',
                'descricao': entrada['descricao'] or 'Entrada',
                'data': entrada['data'],
                'valor': float(entrada['valor']),
                'detalhes': entrada['detalhes'] or '-'
            })
        
        for saida in saidas:
            transacoes.append({
                'tipo': 'saida',
                'descricao': saida['descricao'] or 'Pagamento',
                'data': saida['data'],
                'valor': float(saida['valor']),
                'detalhes': saida['detalhes'] or '-'
            })
        
        # Ordenar por data (mais recentes primeiro)
        transacoes.sort(key=lambda x: datetime.strptime(x['data'], '%d/%m/%Y'), reverse=True)
        
        return transacoes[:15]  # Retornar apenas as 15 mais recentes
        
    except Exception as e:
        print(f"Erro ao obter últimas transações: {e}")
        return []
    finally:
        conn.close()

@dashboard_finance_bp.route('/')
def dashboard_finance():
    """Rota principal do dashboard"""
    return render_template('financeiro/dashboard.html')

@dashboard_finance_bp.route('/api/resumo')
def api_resumo():
    """API para obter resumo financeiro"""
    resumo = get_financial_summary()
    return jsonify(resumo)

@dashboard_finance_bp.route('/api/fluxo-caixa')
def api_fluxo_caixa():
    """API para obter dados do fluxo de caixa"""
    fluxo = get_fluxo_caixa_mensal()
    return jsonify(fluxo)

@dashboard_finance_bp.route('/api/categorias-despesas')
def api_categorias_despesas():
    """API para obter distribuição de despesas por categoria"""
    categorias = get_categorias_despesas()
    return jsonify(categorias)

@dashboard_finance_bp.route('/api/canais-receita')
def api_canais_receita():
    """API para obter distribuição de receitas por canal"""
    canais = get_canais_receita()
    return jsonify(canais)

@dashboard_finance_bp.route('/api/transacoes')
def api_transacoes():
    """API para obter últimas transações"""
    transacoes = get_ultimas_transacoes()
    return jsonify(transacoes)

@dashboard_finance_bp.route('/api/dados-completos')
def api_dados_completos():
    """API para obter todos os dados do dashboard de uma vez"""
    try:
        dados = {
            'resumo': get_financial_summary(),
            'fluxo_caixa': get_fluxo_caixa_mensal(),
            'categorias_despesas': get_categorias_despesas(),
            'canais_receita': get_canais_receita(),
            'transacoes': get_ultimas_transacoes()
        }
        return jsonify(dados)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

