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
                            "nome": "Lançamentos",
                            "icone": "ri-exchange-line",
                            "url": url_for('lancamento_manual.pagina_lancamento')
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
            "titulo": "Estoque",
            "icone": "ri-store-line",
            "itens": [
                {
                    "nome": "Estoque",
                    "icone": "ri-archive-line",
                    "submenu": [
                        {
                            "nome": "Lançamentos de Estoque",
                            "icone": "ri-input-method-line",
                            "url": url_for('lancamentos_estoque.tela_lancamentos_estoque')
                        },
                        {
                            "nome": "Dashboard",
                            "icone": "ri-bar-chart-2-line",
                            "url": url_for('estoque.dashboard')
                        }
                    ]
                }
            ]
        },
        {
            "titulo": "Produtos",
            "icone": "ri-price-tag-line",
            "itens": [
                {
                    "nome": "Produtos",
                    "icone": "ri-product-hunt-line",
                    "submenu": [
                        {
                            "nome": "Catálogo",
                            "icone": "ri-list-check",
                            "url": url_for('produtos.index')
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
                    "icone": "ri-shopping-bag-line",
                    "submenu": [
                        {
                            "nome": "Mercado Livre",
                            "icone": "ri-store-2-line",
                            "submenu": [
                                {
                                    "nome": "Dashboard ML",
                                    "icone": "ri-dashboard-2-line",
                                    "url": url_for('ml_bp.ml_dashboard')
                                }
                            ]
                        },
                        {
                            "nome": "Shopee",
                            "icone": "ri-global-line",
                            "submenu": [
                                {
                                    "nome": "Dashboard Shopee",
                                    "icone": "ri-dashboard-2-line",
                                    "url": url_for('shopee_bp.dashboard_shopee')
                                }
                            ]
                        },
                        {
                            "nome": "Shein",
                            "icone": "ri-t-shirt-line",
                            "submenu": [
                                {
                                    "nome": "Dashboard Shein",
                                    "icone": "ri-dashboard-2-line",
                                    "url": "#"
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "titulo": "NF-e",
            "icone": "ri-file-text-line",
            "itens": [
                {
                    "nome": "Compras",
                    "icone": "ri-shopping-cart-2-line",
                    "submenu": [
                        {
                            "nome": "Painel NF-e",
                            "icone": "ri-file-list-line",
                            "url": url_for('nfe_bp.painel')
                        },
                        {
                            "nome": "Config. de Unidades",
                            "icone": "ri-settings-3-line",
                            "url": url_for('config_unidades.painel_principal')
                        }
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