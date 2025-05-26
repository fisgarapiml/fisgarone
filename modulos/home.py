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
                        { "nome": "Dashboard", "url": url_for('estoque_bp.estoque_dashboard') }
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
            "titulo": "NF-e",
            "itens": [
                {
                    "nome": "NF-e",
                    "icone": "fas fa-file-invoice",
                    "submenu": [
                        # Atualizado para usar o endpoint correto do blueprint de NF-e
                        { "nome": "Painel NF-e", "url": url_for('nfe_bp.painel') }
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