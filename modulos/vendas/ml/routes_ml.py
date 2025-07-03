# /modulos/vendas/routes_ml.py
from flask import Blueprint, jsonify
from .full_ml import FullMercadoLivre

ml_bp = Blueprint('mercado_livre', __name__, url_prefix='/mercado_livre')
full_ml = FullMercadoLivre()

@ml_bp.route('/<account_name>')
def dashboard(account_name):
    return full_ml.render_dashboard(account_name)

@ml_bp.route('/<account_name>/refresh')
def refresh(account_name):
    try:
        full_ml.get_sales_data(account_name)
        full_ml.get_product_data(account_name)
        full_ml.calculate_metrics(account_name)
        return jsonify({'status': 'success', 'message': 'Dados atualizados com sucesso'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@ml_bp.route('/<account_name>/data')
def data(account_name):
    dashboard_data = full_ml.get_dashboard_data(account_name)
    return jsonify(dashboard_data) if dashboard_data else jsonify({'error': 'Failed to get data'}), 500