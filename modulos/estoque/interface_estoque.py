from flask import Blueprint, render_template, request, redirect
import sqlite3

estoque_interface = Blueprint('estoque_interface', __name__)

@estoque_interface.route('/estoques')
def dashboard():
    conn = sqlite3.connect('grupo_fisgar.db')
    cursor = conn.cursor()
    total = cursor.execute("SELECT SUM(quantidade) FROM produtos_processados").fetchone()[0] or 0
    abaixo = cursor.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade < 10").fetchone()[0]
    zerados = cursor.execute("SELECT COUNT(*) FROM produtos_processados WHERE quantidade = 0").fetchone()[0]
    conn.close()
    return render_template('estoque/dashboard.html', total=total, abaixo=abaixo, zerados=zerados)

@estoque_interface.route('/estoque/inventario')
def inventario():
    conn = sqlite3.connect('grupo_fisgar.db')
    cursor = conn.cursor()
    produtos = cursor.execute("SELECT * FROM produtos_processados").fetchall()
    conn.close()
    return render_template('estoque/inventario.html', produtos=produtos)

@estoque_interface.route('/estoque/adicionar', methods=['GET', 'POST'])
def adicionar():
    if request.method == 'POST':
        nome = request.form['nome']
        quantidade = request.form['quantidade']
        conn = sqlite3.connect('grupo_fisgar.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO produtos_processados (nome, quantidade) VALUES (?, ?)", (nome, quantidade))
        conn.commit()
        conn.close()
        return redirect('/estoque/inventario')
    return render_template('estoque/formulario.html', produto=None)

@estoque_interface.route('/estoque/editar/<int:codigo>', methods=['GET', 'POST'])
def editar(codigo):
    conn = sqlite3.connect('grupo_fisgar.db')
    cursor = conn.cursor()
    if request.method == 'POST':
        nome = request.form['nome']
        quantidade = request.form['quantidade']
        cursor.execute("UPDATE produtos_processados SET nome = ?, quantidade = ? WHERE codigo = ?", (nome, quantidade, codigo))
        conn.commit()
        conn.close()
        return redirect('/estoque/inventario')
    produto = cursor.execute("SELECT * FROM produtos_processados WHERE codigo = ?", (codigo,)).fetchone()
    conn.close()
    return render_template('estoque/formulario.html', produto=produto)

@estoque_interface.route('/estoque/excluir/<int:codigo>')
def excluir(codigo):
    conn = sqlite3.connect('grupo_fisgar.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM produtos_processados WHERE codigo = ?", (codigo,))
    conn.commit()
    conn.close()
    return redirect('/estoque/inventario')
