from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import sqlite3

usuarios_bp = Blueprint('usuarios', __name__, url_prefix='/usuarios',
                        template_folder='templates', static_folder='static')

def get_db():
    db_path = current_app.config['DATABASE']
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

# Página de login
@usuarios_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        senha = request.form['senha']
        db = get_db()
        usuario = db.execute("SELECT * FROM usuarios WHERE email = ?", (email,)).fetchone()
        if usuario and check_password_hash(usuario['senha_hash'], senha):
            session['usuario_id'] = usuario['id']
            session['usuario_nome'] = usuario['nome']
            session['usuario_tipo'] = usuario['tipo']
            return redirect(url_for('lancamento_manual.pagina_lancamento'))
        else:
            flash('Usuário ou senha inválidos.', 'danger')
    return render_template('login.html')

@usuarios_bp.route('/esqueci_senha', methods=['GET', 'POST'])
def esqueci_senha():
    # Placeholder: exibe tela "Em breve" ou implementa fluxo real depois
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        # Aqui pode adicionar lógica real no futuro
        return render_template('esqueci_senha.html', mensagem="Se este e-mail estiver cadastrado, enviaremos instruções.")
    return render_template('esqueci_senha.html')


@usuarios_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('usuarios.login'))

@usuarios_bp.route('/novo', methods=['GET', 'POST'])
def novo_usuario():
    if session.get('usuario_tipo') != 'admin':
        return redirect(url_for('usuarios.login'))
    if request.method == 'POST':
        nome = request.form['nome'].strip()
        email = request.form['email'].strip().lower()
        senha = request.form['senha']
        tipo = request.form.get('tipo', 'comum')
        db = get_db()
        if db.execute("SELECT 1 FROM usuarios WHERE email = ?", (email,)).fetchone():
            flash('E-mail já cadastrado.', 'danger')
        else:
            senha_hash = generate_password_hash(senha)
            db.execute("INSERT INTO usuarios (nome, email, senha_hash, tipo, data_cadastro) VALUES (?, ?, ?, ?, ?)",
                       (nome, email, senha_hash, tipo, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
            db.commit()
            flash('Usuário cadastrado com sucesso!', 'success')
            return redirect(url_for('usuarios.gerenciar'))
    return render_template('novo_usuario.html')

@usuarios_bp.route('/gerenciar')
def gerenciar():
    if session.get('usuario_tipo') != 'admin':
        return redirect(url_for('usuarios.login'))
    db = get_db()
    usuarios = db.execute("SELECT id, nome, email, tipo, data_cadastro FROM usuarios ORDER BY id").fetchall()
    return render_template('gerenciar_usuarios.html', usuarios=usuarios)
