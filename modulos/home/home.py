from flask import Blueprint, jsonify, url_for, render_template
from flask import current_app

bp_home = Blueprint('bp_home', __name__)

@bp_home.route('/')
def index():
    return render_template('home/index.html')

@bp_home.route('/api/menu')
def get_menu():
    menu = [
        {
            "titulo": "Principal",
            "icone": "ri-home-line",
            "itens": [
                {
                    "nome": "Painel",
                    "icone": "ri-dashboard-line",
                    "url": url_for('bp_home.index')
                }
            ]
        },
        {
            "titulo": "Financeiro",
            "icone": "ri-wallet-line",
            "itens": [
                {
                    "nome": "Financeiro",
                    "icone": "ri-bank-line",
                    "submenu": [
                        {
                            "nome": "Contas a Pagar",
                            "icone": "ri-money-dollar-circle-line",
                            "url": url_for('contas_a_pagar_bp.contas_a_pagar')
                        },
                        {
                            "nome": "Parâmetros Financeiros",
                            "icone": "ri-settings-5-fill",
                            "url": url_for('parametros_bp.tela_parametros')
                        },
                        {
                            "nome": "Lançamentos",
                            "icone": "ri-exchange-line",
                            "url": url_for('financeiro/lancamento_manual.lancamento')
                        },
                        {
                            "nome": "Fluxo de Caixa",
                            "icone": "ri-flow-chart",
                            "url": url_for('cards_bp.get_cards')
                        }
                    ]
                }
            ]
        },
        {
            "titulo": "Vendas",
            "icone": "ri-shopping-cart-line",
            "itens": [
                {
                    "nome": "Vendas",
                    "icone": "ri-bank-line",
                    "submenu": [
                        {
                            "nome": "Mercado Livre",
                            "icone": "ri-store-2-line",
                            "url": url_for('ml_bp.dashboard_vendas_ml')
                        },
                        {
                            "nome": "Shopee",
                            "icone": "ri-shopping-bag-3-line",
                            "url": url_for('shopee_bp.dashboard_shopee')
                        }
                        # Adicione outros marketplaces aqui
                    ]
                }
            ]
        }
    ]
    return jsonify(menu)


@bp_home.route('/debug-routes')
def debug_routes():
    routes = []
    for rule in current_app.url_map.iter_rules():
        if not rule.endpoint.startswith('static'):
            routes.append({
                'endpoint': rule.endpoint,
                'methods': list(rule.methods),
                'path': str(rule)
            })
    return jsonify(sorted(routes, key=lambda x: x['endpoint']))