import os
from flask import Flask
import sqlite3

# Inicialização da aplicação
app = Flask(__name__)

# =============================================
# CONFIGURAÇÕES PRINCIPAIS
# =============================================

# Configurações básicas do Flask
app.config.update({
    'SECRET_KEY': 'sua_chave_secreta_aqui',
    'DATABASE': os.path.join(os.path.dirname(__file__), 'grupo_fisgar.db'),
    'COMPRAS_XML': os.path.join(os.path.dirname(__file__), 'compras_xml'),
    'UPLOAD_FOLDER': 'uploads'
})

# =============================================
# VERIFICAÇÃO DE ESTRUTURA
# =============================================

# Criar pastas necessárias se não existirem
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['COMPRAS_XML'], exist_ok=True)

# Verificação do banco de dados
if not os.path.exists(app.config['DATABASE']):
    raise FileNotFoundError(f"Arquivo do banco de dados não encontrado: {app.config['DATABASE']}")


# =============================================
# FUNÇÕES AUXILIARES
# =============================================

def get_db_connection():
    """Estabelece conexão com o banco de dados SQLite"""
    conn = sqlite3.connect(app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


app.get_db = get_db_connection  # Disponibiliza a função globalmente

# =============================================
# REGISTRO DE BLUEPRINTS
# =============================================

# Importação e registro dos blueprints
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
from modulos.estoque.estoque_dashboard import estoque_bp
from modulos.estoque.api_estoque import api_estoque_bp  # Importação tardia para evitar circular imports

app.register_blueprint(estoque_interface_bp, url_prefix='/estoque/interface')
app.register_blueprint(estoque_bp, url_prefix='/estoque/dashboard')
app.register_blueprint(api_estoque_bp, url_prefix='/api/estoque')

# Produtos e NF-e
from modulos.produtos.produtos_dashboard import produtos_bp
from modulos.nfe.salvar_produto import salvar_produto_bp
from modulos.configuracoes_unidade import config_unidades_bp
from modulos.nfe.painel_nfe import nfe_bp



app.register_blueprint(produtos_bp, url_prefix='/produtos')
app.register_blueprint(salvar_produto_bp, url_prefix='/nfe/produtos')
app.register_blueprint(nfe_bp)
app.register_blueprint(config_unidades_bp)

# =============================================
# INICIALIZAÇÃO
# =============================================

if __name__ == '__main__':
    # Criar pastas se não existirem
    os.makedirs(app.config['COMPRAS_XML'], exist_ok=True)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    app.run(debug=True)