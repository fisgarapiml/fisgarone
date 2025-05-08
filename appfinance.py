from flask import Flask
import os

# Importação dos blueprints
from modulos.estoque.interface_estoque import estoque_interface
from modulos.estoque.api_estoque import api_estoque
from modulos.financeiro.contas_a_pagar import contas_a_pagar_bp
from modulos.financeiro.cards import cards_bp
from modulos.financeiro.lancamento_manual import lancamento_manual_bp
from modulos.estoque.estoque_dashboard import estoque_bp
from modulos.produtos.produtos_dashboard import produtos_bp
from modulos.nfe.salvar_produto import salvar_produto_bp
from modulos.nfe.config_unidades import config_unidades_bp
from modulos.nfe import nfe_bp
from modulos.home import bp_home as home_bp

# Inicialização da aplicação
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'grupo_fisgar.db')
app.config['TEMPLATES_AUTO_RELOAD'] = True

def get_db_connection():
    import sqlite3
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# Verificação do banco de dados
if not os.path.exists(app.config['DATABASE']):
    raise FileNotFoundError(f"Arquivo do banco de dados não encontrado: {app.config['DATABASE']}")

app.get_db = get_db_connection

# Registro dos Blueprints
app.register_blueprint(estoque_interface)
app.register_blueprint(api_estoque)
app.register_blueprint(contas_a_pagar_bp)
app.register_blueprint(cards_bp)
app.register_blueprint(lancamento_manual_bp)
app.register_blueprint(estoque_bp)
app.register_blueprint(produtos_bp)
app.register_blueprint(salvar_produto_bp)
app.register_blueprint(config_unidades_bp)
app.register_blueprint(nfe_bp)
app.register_blueprint(home_bp)  # Registrado como os demais

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)
