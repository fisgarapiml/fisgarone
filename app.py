import os
import sqlite3

from flask import Flask, g, current_app # Importe 'g' e 'current_app'

# Inicialização da aplicação
app = Flask(__name__)

# Configurações básicas do Flask
app.config.update({
    'SECRET_KEY': 'sua_chave_secreta_aqui',
    'DATABASE': os.path.join(os.path.dirname(__file__), 'fisgarone.db'),
    'COMPRAS_XML': os.path.join(os.path.dirname(__file__), 'compras_xml'),
    'UPLOAD_FOLDER': 'uploads',
    'SHOPEE_DASHBOARD': {
        'REFRESH_INTERVAL': 300,
        'MAX_DATA_DAYS': 365,
        'NEON_THEME_COLORS': {
            'primary': '#0066ff',
            'secondary': '#00ff88',
            'accent': '#aa00ff',
            'danger': '#ff5555'
        }
    }
})

# Verificação de estrutura
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['COMPRAS_XML'], exist_ok=True)

if not os.path.exists(app.config['DATABASE']):
    raise FileNotFoundError(f"Arquivo do banco de dados não encontrado: {app.config['DATABASE']}")

# --- Função de Conexão com o Banco de Dados (Mantida para ser usada pelos Blueprints) ---
def get_db_connection():
    """
    Função auxiliar para estabelecer uma conexão com o banco de dados SQLite.
    Usa o objeto `g` para armazenar a conexão por requisição, garantindo reuso.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(current_app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row # Retorna as linhas como objetos de dicionário (acessíveis por nome da coluna)
    return g.db

# Adiciona a função de conexão como um atributo da aplicação para ser usada pelos Blueprints
app.get_db = get_db_connection

# --- Função para Fechar a Conexão do Banco de Dados ---
@app.teardown_appcontext
def close_db_connection(exception):
    """
    Fecha a conexão com o banco de dados ao final do contexto da aplicação (requisição).
    """
    db = g.pop('db', None)
    if db is not None:
        db.close()


# Registro de blueprints (Seu código original, com a adição do shopee Dashboard)
from modulos.home.home import bp_home
app.register_blueprint(bp_home)

# Financeiro
from modulos.financeiro.contas_a_pagar import contas_a_pagar_bp
from modulos.financeiro.cards import cards_bp
from modulos.financeiro.lancamento_manual import lancamento_manual_bp
from modulos.financeiro.contas_edicao import contas_edicao_bp
from modulos.financeiro.parametros import parametros_bp
from modulos.financeiro.entradas import bp as financeiro_bp

# Vendas
from modulos.vendas.ml.ml import ml_bp
from modulos.vendas.shopee.dashboard_shopee import shopee_bp


app.register_blueprint(contas_a_pagar_bp, url_prefix='/contas-a-pagar')
app.register_blueprint(cards_bp, url_prefix='/financeiro/cards')
app.register_blueprint(lancamento_manual_bp, url_prefix='/financeiro/lancamentos')
app.register_blueprint(contas_edicao_bp)
app.register_blueprint(parametros_bp)
app.register_blueprint(financeiro_bp)

# Vendas
app.register_blueprint(ml_bp)
app.register_blueprint(shopee_bp, url_prefix='/modulos/vendas')



if __name__ == '__main__':
    print(f"Banco de dados configurado: {app.config['DATABASE']}")
    if not os.path.exists(app.config['DATABASE']):
        print(f"ATENÇÃO: O arquivo do banco de dados '{app.config['DATABASE']}' NÃO foi encontrado.")
        print("Certifique-se de que 'fisgarone.db' esteja na raiz do seu projeto.")
        print("Se você ainda não o tem, execute 'create_db.py' APENAS PARA TESTE COM DADOS DE EXEMPLO.")
    app.run(debug=True)

