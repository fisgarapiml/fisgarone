import sqlite3
from werkzeug.security import generate_password_hash
from datetime import datetime

# Caminho do banco (ajustado conforme sua estrutura)
db_path = "grupo_fisgar.db"

# Dados do admin inicial
nome = "Admin"
email = "admin@fisgarone.com.br"
senha = "black@2024"  # Troque para uma senha forte!

# Gera o hash seguro da senha
senha_hash = generate_password_hash(senha)
data_cadastro = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

with sqlite3.connect(db_path) as con:
    cur = con.cursor()
    cur.execute("""
        INSERT INTO usuarios (nome, email, senha_hash, tipo, data_cadastro)
        VALUES (?, ?, ?, ?, ?)
    """, (nome, email, senha_hash, 'admin', data_cadastro))
    con.commit()

print("\nUsuário ADMIN criado com sucesso!")
print(f"Login: {email}")
print(f"Senha: {senha}\n")
