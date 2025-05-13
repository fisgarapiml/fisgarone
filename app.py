from flask import Flask
import os

# Importação dos blueprints (todos devem terminar com _bp)
from modulos.estoque.interface_estoque import estoque_interface_bp
from modulos.financeiro.contas_a_pagar import contas_a_pagar_bp
from modulos.financeiro.cards import cards_bp
from modulos.financeiro.lancamento_manual import lancamento_manual_bp
from modulos.estoque.estoque_dashboard import estoque_bp
from modulos.produtos.produtos_dashboard import produtos_bp
from modulos.nfe.salvar_produto import salvar_produto_bp
from modulos.nfe.config_unidades import config_unidades_bp
from modulos.nfe.painel_nfe import nfe_bp
from modulos.home import bp_home
from modulos.auth import auth as auth_blueprint

# Inicialização da aplicação
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'grupo_fisgar.db')
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

def get_db_connection():
    import sqlite3
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn

# Verificação do banco de dados
if not os.path.exists(app.config['DATABASE']):
    raise FileNotFoundError(f"Arquivo do banco de dados não encontrado: {app.config['DATABASE']}")

app.get_db = get_db_connection

# Registro dos blueprints
app.register_blueprint(bp_home)

# Financeiro
app.register_blueprint(contas_a_pagar_bp, url_prefix='/contas-a-pagar')
app.register_blueprint(cards_bp, url_prefix='/financeiro/cards')
app.register_blueprint(lancamento_manual_bp, url_prefix='/financeiro/lancamentos')

# Estoque
app.register_blueprint(estoque_interface_bp, url_prefix='/estoque/interface')
app.register_blueprint(estoque_bp, url_prefix='/estoque/dashboard')

# Importação tardia para evitar erro de circular import com flask_socketio
from modulos.estoque.api_estoque import api_estoque_bp
app.register_blueprint(api_estoque_bp, url_prefix='/api/estoque')

# Produtos e NF-e
app.register_blueprint(produtos_bp, url_prefix='/produtos')
app.register_blueprint(salvar_produto_bp, url_prefix='/nfe/produtos')
app.register_blueprint(config_unidades_bp, url_prefix='/nfe/unidades')
app.register_blueprint(nfe_bp, url_prefix='/nfe/painel')

#Usuarios
app.register_blueprint(auth_blueprint)

from flask_login import LoginManager
from modulos.usuario_model import Usuario

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, email, senha_hash, nivel_acesso FROM usuarios WHERE id = ?", (user_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return Usuario(*row)
    return None


if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)

