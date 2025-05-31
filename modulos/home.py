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
            "itens": [
                {
                    "nome": "Painel",
                    "icone": "fas fa-tachometer-alt",
                    "url": url_for('bp_home.index')
                }
            ]
        },
        {
            "titulo": "Financeiro",
            "itens": [
                {
                    "nome": "Financeiro",
                    "icone": "fas fa-wallet",
                    "submenu": [
                        { "nome": "Contas a Pagar", "url": url_for('contas_a_pagar_bp.contas_a_pagar') },
                        { "nome": "Lançamentos", "url": url_for('lancamento_manual.pagina_lancamento') },
                        { "nome": "Fluxo de Caixa", "url": url_for('cards_bp.get_cards') }
                    ]
                }
            ]
        },
        {
            "titulo": "Estoque",
            "itens": [
                {
                    "nome": "Estoque",
                    "icone": "fas fa-boxes",
                    "submenu": [
                        { "nome": "Interface", "url": url_for('estoque_interface_bp.interface') },
                        { "nome": "Dashboard", "url": url_for('estoque.dashboard') }
                    ]
                }
            ]
        },
        {
            "titulo": "Produtos",
            "itens": [
                {
                    "nome": "Produtos",
                    "icone": "fas fa-tags",
                    "submenu": [
                        { "nome": "Catálogo", "url": url_for('produtos.index') }
                    ]
                }
            ]
        },
        {
            "titulo": "Vendas",
            "itens": [
                {
                    "nome": "Vendas",
                    "icone": "fas fa-shopping-cart",
                    "submenu": [
                        {
                            "nome": "Mercado Livre",
                            "submenu": [
                                {
                                    "nome": "Dashboard ML",
                                    "url": url_for('ml_bp.dashboard_vendas_ml')  # <-- **NOME DO ENDPOINT DO DASHBOARD ML**
                                }
                                # Aqui adiciona futuras telas do ML
                            ]
                        },
                        {
                            "nome": "Shopee",
                            "submenu": [
                                # Adicione as telas Shopee quando criar
                                # { "nome": "Dashboard Shopee", "url": url_for('shopee_bp.dashboard') }
                            ]
                        },
                        {
                            "nome": "Shein",
                            "submenu": [
                                # Adicione as telas Shein quando criar
                                # { "nome": "Dashboard Shein", "url": url_for('shein_bp.dashboard') }
                            ]
                        }
                    ]
                }
            ]
        },
        {
            "titulo": "NF-e",
            "itens": [
                {
                    "nome": "Compras",
                    "icone": "fas fa-file-invoice",
                    "submenu": [
                        { "nome": "Painel NF-e", "url": url_for('nfe_bp.painel') },
                        { "nome": "Config. de Unidades", "url": url_for('config_unidades.painel_principal') }
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
