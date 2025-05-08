from flask import Blueprint, render_template, jsonify, url_for, current_app
from datetime import datetime
import sqlite3

# Blueprint corrigido com nome consistente
bp_home = Blueprint('bp_home', __name__, template_folder='templates/home')

def get_db():
    """Conexão com o banco de dados"""
    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

@bp_home.route('/')
def index():
    """Rota principal do dashboard"""
    try:
        return render_template('home/index.html', 
                            ano_atual=datetime.now().year)
    except Exception as e:
        current_app.logger.error(f"Erro na página inicial: {str(e)}")
        return render_template('error.html'), 500

@bp_home.route('/api/dashboard')
def dashboard_data():
    """API para dados do dashboard"""
    try:
        db = get_db()
        dados = {
            'financeiro': get_financeiro_data(db),
            'estoque': get_estoque_data(db),
            'sistema': {
                'modulos_ativos': 8,
                'nome': 'FisgarOne'
            }
        }
        return jsonify(dados)
    except Exception as e:
        current_app.logger.error(f"Erro no dashboard: {str(e)}")
        return jsonify({"error": str(e)}), 500
    finally:
        db.close()

@bp_home.route('/api/menu')
def get_menu():
    """Retorna a estrutura completa do menu com todas as rotas"""
    menu = [
        {
            "titulo": "Principal",
            "itens": [
                {
                    "nome": "Painel",
                    "icone": "fas fa-tachometer-alt",
                    "url": "/"
                }
            ]
        },
        {
            "titulo": "Financeiro",
            "itens": [
                {
                    "nome": "Contas a Pagar",
                    "icone": "fas fa-money-bill-wave",
                    "url": url_for('contas_a_pagar_bp.contas_a_pagar')  # Nome exato do blueprint
                },
                {
                    "nome": "Lançamentos",
                    "icone": "fas fa-pen-fancy",
                    "url": "/lancamento_manual"  # Rota do seu blueprint
                },
                {
                    "nome": "Fluxo de Caixa",
                    "icone": "fas fa-chart-line",
                    "url": "/fluxo_caixa"  # Adicione sua rota real
                }
            ]
        },
        {
            "titulo": "Estoque",
            "itens": [
                {
                    "nome": "Dashboard",
                    "icone": "fas fa-boxes",
                    "url": "/estoque_dashboard"
                },
                {
                    "nome": "Interface",
                    "icone": "fas fa-warehouse",
                    "url": "/estoque_interface"
                }
            ]
        }
    ]
    return jsonify(menu)
# Funções auxiliares
def get_financeiro_data(db):
    """Busca dados financeiros"""
    result = db.execute(
        "SELECT COUNT(*) as total FROM contas_pagar WHERE status = 'pendente'"
    ).fetchone()
    return {
        'contas_pagar': result['total'] if result else 0,
        'contas_receber': 0  # Implemente conforme necessário
    }

def get_estoque_data(db):
    """Busca dados de estoque"""
    result = db.execute("SELECT COUNT(*) as total FROM produtos").fetchone()
    return {
        'total_itens': result['total'] if result else 0,
        'baixo_estoque': 0  # Implemente conforme necessário
    }