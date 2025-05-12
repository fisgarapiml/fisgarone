from flask import Blueprint, jsonify, url_for, render_template
from flask import current_app  # Modificação importante aqui

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
                    "nome": "Contas a Pagar",
                    "icone": "fas fa-money-bill-wave",
                    "url": url_for('contas_a_pagar_bp.contas_a_pagar')
                },
                {
                    "nome": "Lançamentos",
                    "icone": "fas fa-pen-fancy",
                    "url": url_for('lancamento_manual_bp.lancamento_manual')
                },
                {
                    "nome": "Fluxo de Caixa",
                    "icone": "fas fa-chart-line",
                    "url": url_for('cards_bp.get_cards')
                }
            ]
        },
        {
            "titulo": "Estoque",
            "itens": [
                {
                    "nome": "Interface",
                    "icone": "fas fa-warehouse",
                    "url": url_for('estoque_interface_bp.interface')
                },
                {
                    "nome": "Dashboard",
                    "icone": "fas fa-boxes",
                    "url": url_for('estoque_bp.estoque_dashboard')
                }
            ]
        },
        {
            "titulo": "Produtos",
            "itens": [
                {
                    "nome": "Catálogo",
                    "icone": "fas fa-tags",
                    "url": url_for('produtos.index')  # ← endpoint real conforme debug
                }
            ]
        },
        {
            "titulo": "NF-e",
            "itens": [
                {
                    "nome": "Painel NF-e",
                    "icone": "fas fa-file-invoice",
                    "url": url_for('nfe.painel')  # ← endpoint real
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