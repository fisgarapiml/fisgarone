
from flask import Flask
import os

# 1) Importe todos os Blueprints
from modulos.estoque.interface_estoque    import estoque_interface
from modulos.estoque.api_estoque          import api_estoque
from modulos.financeiro.contas_pagar_view import contas_pagar_bp
from modulos.financeiro.cards              import cards_bp
from modulos.financeiro.lancamento_manual  import lancamento_manual_bp
from modulos.estoque.estoque_dashboard     import estoque_bp
from modulos.produtos.produtos_dashboard   import produtos_bp
from modulos.nfe.salvar_produto           import salvar_produto_bp
from modulos.nfe.config_unidades          import config_unidades_bp
from modulos.nfe                          import nfe_bp

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui'
app.config['DATABASE'] = os.path.join(os.path.dirname(__file__), 'grupo_fisgar.db')

def get_db_connection():
    try:
        from flask import current_app
        import sqlite3
        conn = sqlite3.connect(current_app.config['DATABASE'])
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print(f"Erro ao conectar ao banco de dados: {str(e)}")
        raise

# Verificação do banco de dados
if not os.path.exists(app.config['DATABASE']):
    raise FileNotFoundError(f"Arquivo do banco de dados não encontrado: {app.config['DATABASE']}")
app.get_db = get_db_connection
# Registro do Blueprint
app.register_blueprint(estoque_interface)   # interface web do módulo Estoque
app.register_blueprint(api_estoque)         # API REST do módulo Estoque
app.register_blueprint(contas_pagar_bp)     # financeiro – contas a pagar
app.register_blueprint(cards_bp)            # financeiro – cards
app.register_blueprint(lancamento_manual_bp)# financeiro – lançamento manual
app.register_blueprint(estoque_bp)          # dashboard alternativo de Estoque
app.register_blueprint(produtos_bp)         # dashboard de Produtos
app.register_blueprint(salvar_produto_bp)   # NFE – salvar produto
app.register_blueprint(config_unidades_bp)  # NFE – configuração de unidades
app.register_blueprint(nfe_bp)              # NFE – demais rotas



if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(debug=True)