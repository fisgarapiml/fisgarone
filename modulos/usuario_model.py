# /fisgarone/modulos/usuario_model.py

from flask_login import UserMixin

class Usuario(UserMixin):
    def __init__(self, id, nome, email, senha_hash, nivel_acesso):
        self.id = id
        self.nome = nome
        self.email = email
        self.senha_hash = senha_hash
        self.nivel_acesso = nivel_acesso

    def get_id(self):
        return str(self.id)
