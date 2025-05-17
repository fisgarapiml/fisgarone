from flask import Blueprint, render_template, request, jsonify
import sqlite3
from datetime import datetime

ponto_bp = Blueprint('ponto_bp', __name__, template_folder='templates', static_folder='static')

# Criação automática da tabela
def criar_tabela():
    conn = sqlite3.connect('grupo_fisgar.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS registro_ponto (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            funcionario TEXT,
            data TEXT,
            hora TEXT,
            tipo TEXT
        )
    ''')
    conn.commit()
    conn.close()

@ponto_bp.route('/ponto')
def ponto():
    criar_tabela()  # Garante que a tabela exista
    return render_template('ponto.html')

@ponto_bp.route('/registrar_ponto', methods=['POST'])
def registrar_ponto():
    dados = request.get_json()
    nome = dados.get('funcionario')
    tipo = dados.get('tipo', 'Entrada')  # padrão

    agora = datetime.now()
    data = agora.strftime('%d/%m/%Y')
    hora = agora.strftime('%H:%M:%S')

    conn = sqlite3.connect('grupo_fisgar.db')
    c = conn.cursor()
    c.execute('INSERT INTO registro_ponto (funcionario, data, hora, tipo) VALUES (?, ?, ?, ?)',
              (nome, data, hora, tipo))
    conn.commit()
    conn.close()

    return jsonify({'status': 'ok', 'hora': hora, 'data': data})
