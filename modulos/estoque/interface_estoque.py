from flask import Blueprint, render_template, current_app
import sqlite3
from functools import wraps

estoque_interface_bp = Blueprint('estoque_interface_bp', __name__)


def get_db_connection():
    """Obtém conexão com o banco de dados de forma segura"""
    if 'DATABASE' not in current_app.config:
        raise RuntimeError("Configuração 'DATABASE' não encontrada")

    conn = sqlite3.connect(current_app.config['DATABASE'])
    conn.row_factory = sqlite3.Row
    return conn


def db_connection_required(f):
    """Decorator para gerenciar conexões com o banco"""

    @wraps(f)
    def decorated_function(*args, **kwargs):
        conn = None
        try:
            conn = get_db_connection()
            return f(conn, *args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Erro de banco de dados: {str(e)}")
            return render_template('error.html', message="Erro ao acessar o banco de dados"), 500
        finally:
            if conn:
                conn.close()

    return decorated_function


@estoque_interface_bp.route('/')
@db_connection_required
def interface(conn):
    """Rota principal da interface de estoque"""
    try:
        cursor = conn.cursor()
        # Suas consultas ao banco aqui
        return render_template('estoque/interface.html')
    except Exception as e:
        current_app.logger.error(f"Erro na interface: {str(e)}")
        return render_template('error.html', message="Erro ao carregar a interface"), 500