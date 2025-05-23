# app.py

from flask import Flask
from dotenv import load_dotenv
from models import db  # SQLAlchemy models, deve estar preparado para PostgreSQL
import os
from datetime import datetime



# ========== CARREGAMENTO DE VARIÁVEIS DE AMBIENTE ==========
load_dotenv()  # Garante que .env (na raiz) será carregado

# ========== INICIALIZAÇÃO DO FLASK ==========
app = Flask(__name__)

# ========== CONFIGURAÇÕES PRINCIPAIS ==========
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# ========== CONFIGURAÇÃO DO POSTGRESQL (Nuvem) ==========
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)  # models.py já deve estar pronto para usar PostgreSQL

# ========== FUNÇÃO DE CONEXÃO SQLITE (usada APENAS pelos módulos antigos) ==========
def get_db_connection():
    import sqlite3
    db_path = os.path.join(os.path.dirname(__file__), 'grupo_fisgar.db')
    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Arquivo do banco de dados não encontrado: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# ========== CONTEXTO DE DATA/HORA (para Jinja/templates) ==========
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

# ========== IMPORTAÇÃO DOS BLUEPRINTS ==========
from modulos.estoque.interface_estoque import estoque_interface_bp
from modulos.financeiro.contas_a_pagar import contas_a_pagar_bp
from modulos.financeiro.cards import cards_bp
from modulos.financeiro.lancamento_manual import lancamento_manual_bp
from modulos.estoque.estoque_dashboard import estoque_bp
from modulos.produtos.produtos_dashboard import produtos_bp
from modulos.nfe.salvar_produto import salvar_produto_bp
from modulos.nfe.config_unidades import config_unidades_bp
from modulos.home import bp_home
# from modulos.auth import auth as auth_blueprint
from modulos.financeiro.contas_edicao import contas_edicao_bp
from modulos.ponto.rotas import ponto_bp
from modulos.usuarios.routes import usuarios_bp
from modulos.estoque.api_estoque import api_estoque_bp
from modulos.nfe.painel_nfe import nfe_bp


# ========== REGISTRO DOS BLUEPRINTS ==========
# Módulo de Usuários/Home
app.register_blueprint(usuarios_bp)
app.register_blueprint(bp_home)

# Módulo Financeiro (com prefixos)
app.register_blueprint(contas_a_pagar_bp, url_prefix='/contas-a-pagar')         # Migrado p/ PostgreSQL
app.register_blueprint(cards_bp, url_prefix='/financeiro/cards')                # Migrado p/ PostgreSQL
app.register_blueprint(lancamento_manual_bp, url_prefix='/financeiro/lancamentos') # Migrado p/ PostgreSQL
app.register_blueprint(contas_edicao_bp)                                        # Migrado p/ PostgreSQL

# Módulo Estoque (usando SQLite local)
app.register_blueprint(estoque_interface_bp, url_prefix='/estoque/interface')
app.register_blueprint(estoque_bp, url_prefix='/estoque/dashboard')
app.register_blueprint(api_estoque_bp, url_prefix='/api/estoque')

# Produtos e NF-e (usando SQLite local)
app.register_blueprint(produtos_bp, url_prefix='/produtos')
app.register_blueprint(salvar_produto_bp, url_prefix='/nfe/produtos')
app.register_blueprint(config_unidades_bp, url_prefix='/nfe/unidades')
app.register_blueprint(nfe_bp, url_prefix='/nfe')

# Usuários / Ponto
app.register_blueprint(ponto_bp)

# ========== CRIAÇÃO DAS TABELAS NO POSTGRESQL (somente módulos migrados) ==========
with app.app_context():
    db.create_all()

# ========== EXECUÇÃO ==========
if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)

