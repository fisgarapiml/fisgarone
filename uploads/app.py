import os
import sqlite3

from flask import Flask, g, current_app # Importe 'g' e 'current_app'

# Inicialização da aplicação
app = Flask(__name__)

# --- Seu código original para processamento e integração ---
from contas_pagar_integracao import ContasPagarIntegracao

# Chamadas fora do contexto da aplicação, se necessário (verifique a ordem de execução)
# consolidar_estoque_produtos_nfe() # Descomente se for para ser executado ao iniciar o app

# O 'with app.app_context():' garante que o app esteja configurado para a inicialização
with app.app_context():
    contas_pagar = ContasPagarIntegracao(app)

# Configurações básicas do Flask
app.config.update({
    'SECRET_KEY': 'sua_chave_secreta_aqui',
    'DATABASE': os.path.join(os.path.dirname(__file__), 'grupo_fisgar.db'),
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


# Registro de blueprints (Seu código original, com a adição do Shopee Dashboard)
from modulos.home import bp_home
app.register_blueprint(bp_home)

# Financeiro
from modulos.financeiro.contas_a_pagar import contas_a_pagar_bp
from modulos.financeiro.cards import cards_bp
from modulos.financeiro.lancamento_manual import lancamento_manual_bp
from modulos.financeiro.contas_edicao import contas_edicao_bp
from modulos.financeiro.dashboard import dashboard

app.register_blueprint(contas_a_pagar_bp, url_prefix='/contas-a-pagar')
app.register_blueprint(cards_bp, url_prefix='/financeiro/cards')
app.register_blueprint(lancamento_manual_bp, url_prefix='/financeiro/lancamentos')
app.register_blueprint(contas_edicao_bp)
app.register_blueprint(dashboard)

# Estoque
from modulos.estoque.interface_estoque import estoque_interface_bp
from modulos.estoque.api_estoque import api_estoque_bp
from modulos.estoque.estoque import estoque_bp
from modulos.estoque.lancamentos_estoque import lancamentos_estoque_bp

app.register_blueprint(estoque_interface_bp, url_prefix='/estoque/interface')
app.register_blueprint(estoque_bp, url_prefix='/estoque')
app.register_blueprint(api_estoque_bp, url_prefix='/api/estoque')
app.register_blueprint(lancamentos_estoque_bp)

# Produtos e NF-e
from modulos.produtos.produtos_dashboard import produtos_bp

from modulos.configuracoes_unidade import config_unidades_bp
from modulos.nfe.painel_nfe import nfe_bp


app.register_blueprint(produtos_bp, url_prefix='/produtos')

app.register_blueprint(nfe_bp)
app.register_blueprint(config_unidades_bp)


# Vendas

# --- IMPORTANTE: Registro do Blueprint do Dashboard Shopee ---
# Certifique-se de que o caminho para o seu arquivo dashboard_shopee.py está correto:
# modulos/vendas/shopee/dashboard_shopee.py
from modulos.vendas.shopee.dashboard_shopee import shopee_bp
from modulos.vendas.ml import ml_bp

# Registra o Blueprint do dashboard Shopee com o prefixo de URL '/shopee/dashboard'
app.register_blueprint(shopee_bp, url_prefix='/modulos/vendas')
app.register_blueprint(ml_bp)


if __name__ == '__main__':
    print(f"Banco de dados configurado: {app.config['DATABASE']}")
    if not os.path.exists(app.config['DATABASE']):
        print(f"ATENÇÃO: O arquivo do banco de dados '{app.config['DATABASE']}' NÃO foi encontrado.")
        print("Certifique-se de que 'grupo_fisgar.db' esteja na raiz do seu projeto.")
        print("Se você ainda não o tem, execute 'create_db.py' APENAS PARA TESTE COM DADOS DE EXEMPLO.")
    app.run(debug=True)

