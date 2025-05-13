import sqlite3
from werkzeug.security import generate_password_hash

# Conexão direta com o banco na raiz
conn = sqlite3.connect('grupo_fisgar.db')
cursor = conn.cursor()

# Criptografa a senha
senha_hash = generate_password_hash("senha123", method='pbkdf2:sha256')

# Insere o usuário
cursor.execute('''
INSERT INTO usuarios (nome, email, senha_hash, nivel_acesso)
VALUES (?, ?, ?, ?)
''', ("Administrador", "admin@fisgar.com", senha_hash, "admin"))

conn.commit()
conn.close()

print("✅ Usuário criado com sucesso.")
