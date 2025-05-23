from flask import Flask, Blueprint

nfe_bp = Blueprint('nfe', __name__)

@nfe_bp.route('/')
def painel():
    return 'NF-e painel funcionando!'

app = Flask(__name__)
app.register_blueprint(nfe_bp, url_prefix='/nfe')

if __name__ == '__main__':
    app.run(debug=True)
