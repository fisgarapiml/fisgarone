from flask import Blueprint, render_template, request, jsonify
import sqlite3
import os
import xml.etree.ElementTree as ET
from datetime import datetime

config_unidades_bp = Blueprint('config_unidades', __name__)
DB = 'grupo_fisgar.db'
PASTA_XML = 'compras_xml'
NAMESPACE = {'ns': 'http://www.portalfiscal.inf.br/nfe'}

# Criar tabela de configuração de unidade
def criar_tabela_config_unidade():
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS configuracoes_unidade (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo_fornecedor TEXT UNIQUE,
                nome TEXT,
                unidade_compra TEXT,
                qtd_por_volume INTEGER,
                qtd_por_pacote INTEGER,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

# Extrair produtos únicos do XML que ainda não estão na tabela
def extrair_produtos_unicos():
    produtos = {}
    for arquivo in os.listdir(PASTA_XML):
        if not arquivo.endswith('.xml'):
            continue
        try:
            caminho = os.path.join(PASTA_XML, arquivo)
            tree = ET.parse(caminho)
            root = tree.getroot()
            for det in root.findall('.//ns:det', NAMESPACE):
                prod = det.find('ns:prod', NAMESPACE)
                if prod is None:
                    continue
                codigo_node = prod.find('ns:cProd', NAMESPACE)
                nome_node = prod.find('ns:xProd', NAMESPACE)
                unidade_node = prod.find('ns:uCom', NAMESPACE)
                if codigo_node is not None and nome_node is not None:
                    codigo = codigo_node.text.strip()
                    nome = nome_node.text.strip()
                    unidade = unidade_node.text.strip() if unidade_node is not None else ''
                    produtos[codigo] = {
                        'codigo_fornecedor': codigo,
                        'nome': nome,
                        'unidade': unidade
                    }
        except Exception as e:
            print(f"Erro ao processar {arquivo}: {e}")
    return produtos

def filtrar_nao_cadastrados(produtos):
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT codigo_fornecedor FROM configuracoes_unidade")
        ja_cadastrados = {row[0] for row in cur.fetchall()}
        return {
            codigo: dados
            for codigo, dados in produtos.items()
            if codigo not in ja_cadastrados
        }

def buscar_todos_configurados():
    with sqlite3.connect(DB) as conn:
        cur = conn.cursor()
        cur.execute("SELECT * FROM configuracoes_unidade ORDER BY nome")
        colunas = [desc[0] for desc in cur.description]
        return [dict(zip(colunas, row)) for row in cur.fetchall()]
# ROTA PRINCIPAL DA TELA
@config_unidades_bp.route('/config-unidades', methods=['GET'])
def tela_config_unidades():
    criar_tabela_config_unidade()
    todos = extrair_produtos_unicos()
    pendentes = filtrar_nao_cadastrados(todos)
    configurados = buscar_todos_configurados()
    return render_template('config_tabela_unidades.html',
                           produtos=list(pendentes.values()),
                           total=len(pendentes),
                           configurados=configurados,
                           total_configurados=len(configurados))

# SALVAR CONFIGURAÇÃO DE UNIDADE
@config_unidades_bp.route('/config-unidades/salvar', methods=['POST'])
def salvar_config_unidade():
    dados = request.get_json(force=True)
    try:
        with sqlite3.connect(DB) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO configuracoes_unidade (
                    codigo_fornecedor, nome, unidade_compra, qtd_por_volume, qtd_por_pacote
                ) VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(codigo_fornecedor) DO UPDATE SET
                    nome = excluded.nome,
                    unidade_compra = excluded.unidade_compra,
                    qtd_por_volume = excluded.qtd_por_volume,
                    qtd_por_pacote = excluded.qtd_por_pacote
            """, (
                dados['codigo_fornecedor'],
                dados['nome'],
                dados['unidade_compra'],
                int(dados.get('qtd_por_volume', 0)),
                int(dados.get('qtd_por_pacote', 0))
            ))
            conn.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)})
