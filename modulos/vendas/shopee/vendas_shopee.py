import os
import pandas as pd
import sqlite3
import json
from datetime import datetime

def criar_tabela_vendas_shopee():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
    db_path = os.path.join(base_dir, 'fisgarone.db')

    if not os.path.exists(db_path):
        raise FileNotFoundError(f"Banco de dados não encontrado: {db_path}")

    conn = sqlite3.connect(db_path)
    tabelas = pd.read_sql("SELECT name FROM sqlite_master WHERE type='table';", conn)
    if 'pedidos' not in tabelas['name'].tolist():
        raise ValueError("A tabela 'pedidos' não existe no banco de dados.")

    pedidos = pd.read_sql("SELECT * FROM pedidos", conn)
    pedidos['data'] = pd.to_datetime(pedidos['create_time'], errors='coerce')
    pedidos['item_list'] = pedidos['item_list'].apply(json.loads)
    pedidos = pedidos.explode('item_list')
    itens_df = pd.json_normalize(pedidos['item_list'])
    itens_df.columns = [f'item_{col}' for col in itens_df.columns]
    pedidos = pedidos.drop(columns=['item_list']).reset_index(drop=True)
    pedidos = pd.concat([pedidos, itens_df], axis=1)

    def extrair_transportadora(pkg):
        try:
            pacotes = json.loads(pkg)
            if isinstance(pacotes, list) and len(pacotes) > 0:
                return pacotes[0].get('shipping_carrier', '')
        except:
            return ''
        return ''

    pedidos['transportadora'] = pedidos['package_list'].apply(extrair_transportadora)
    pedidos['transportadora'] = pedidos['transportadora'].replace({
        'SBS': 'Shopee Xpress',
        'SPX': 'Shopee Xpress',
        'STANDARD_EXPRESS': 'Shopee Xpress',
        'OTHER_LOGISTICS': 'Outros',
        'INHOUSE': 'Agência Shopee',
        'OWN_DELIVERY': 'Entrega Direta'
    })

    pedidos['preco_unitario'] = pedidos['item_model_discounted_price'].astype(float)
    pedidos['qtd_comprada'] = pedidos['item_model_quantity_purchased'].astype(int)
    pedidos['frete_total'] = pedidos['actual_shipping_fee'].astype(float)
    pedidos['valor_total'] = pedidos['preco_unitario'] * pedidos['qtd_comprada']
    pedidos['itens_pedido'] = pedidos.groupby('order_sn')['order_sn'].transform('count')
    pedidos['frete_unitario'] = pedidos['frete_total'] / pedidos['itens_pedido']
    pedidos['comissao_unitaria'] = (pedidos['valor_total'] * 0.22).round(2)
    pedidos['taxa_fixa'] = (pedidos['qtd_comprada'] * 4.00).round(2)

    pedidos['data_entrega'] = pd.NaT
    pedidos_completos = pedidos['order_status'] == 'COMPLETED'
    data_entregue_valida = pd.to_datetime(pedidos['Data_Entregue'], errors='coerce')
    pedidos.loc[pedidos_completos & data_entregue_valida.notna(), 'data_entrega'] = data_entregue_valida

    pedidos['prazo_entrega_dias'] = None
    pedidos.loc[pedidos['data_entrega'].notna(), 'prazo_entrega_dias'] = \
        (pedidos['data_entrega'] - pedidos['data']).dt.total_seconds() / 86400
    pedidos['prazo_entrega_dias'] = pedidos['prazo_entrega_dias'].round(2)

    final = pedidos.rename(columns={
        'order_sn': 'pedido_id',
        'buyer_user_id': 'comprador_id',
        'order_status': 'status_pedido',
        'account_type': 'tipo_conta',
        'item_item_name': 'nome_item',
        'item_item_sku': 'sku_item',
        'item_model_sku': 'sku_variacao'
    })

    colunas_finais = [
        'pedido_id', 'comprador_id', 'status_pedido', 'tipo_conta', 'data',
        'nome_item', 'sku_item', 'sku_variacao', 'qtd_comprada', 'preco_unitario',
        'valor_total', 'frete_unitario', 'comissao_unitaria', 'taxa_fixa', 'transportadora', 'data_entrega', 'prazo_entrega_dias'
    ]

    final = final[colunas_finais].sort_values(by='valor_total', ascending=False)
    final.to_sql("vendas_shopee", conn, if_exists="replace", index=False)
    conn.close()
    print("✅ Tabela 'vendas_shopee' atualizada com sucesso no banco local.")

if __name__ == "__main__":
    criar_tabela_vendas_shopee()
