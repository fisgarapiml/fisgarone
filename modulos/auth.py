# /fisgarone/modulos/auth.py

from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required
from werkzeug.security import check_password_hash
from modulos.usuario_model import Usuario
import sqlite3

auth = Blueprint('auth', __name__, url_prefix='/auth')

def get_usuario_por_email(email):
    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, nome, email, senha_hash, nivel_acesso FROM usuarios WHERE email = ?", (email,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return Usuario(*row)
    return None

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        senha = request.form['senha']
        usuario = get_usuario_por_email(email)
        if usuario and check_password_hash(usuario.senha_hash, senha):
            login_user(usuario)
            return redirect(url_for('bp_home.index'))
  # ajuste para sua tela inicial
        flash('E-mail ou senha inválidos.', 'erro')
    return render_template('login.html')

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('auth.login'))
