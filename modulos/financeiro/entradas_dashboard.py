import sqlite3
from flask import Blueprint, render_template, current_app
from datetime import datetime
import pandas as pd

entradas_bp = Blueprint("entradas", __name__)

DB_PATH = r"C:\fisgarone\fisgarone.db"

def query_dataframe(query, params=()):
    with sqlite3.connect(DB_PATH) as conn:
        df = pd.read_sql_query(query, conn, params=params)
    return df

@entradas_bp.route("/entradas")
def painel_entradas():
    # ==== CARDS RESUMO ====
    # Entradas Totais (todos os canais)
    df = query_dataframe("""
        SELECT valor_total, status, tipo, data_venda FROM entradas_financeiras
        WHERE data_venda IS NOT NULL
    """)
    total_entradas = df["valor_total"].sum()
    total_recebido = df[df["status"].str.lower().isin(["recebido", "concluido"])]["valor_total"].sum()
    total_pendente = df[df["status"].str.lower().isin(["pendente", "a receber", "aguardando"])]["valor_total"].sum()
    shopee = df[df["tipo"] == "shopee"]["valor_total"].sum()
    ml = df[df["tipo"].str.contains("ml")]["valor_total"].sum()  # aceita ml, mercado livre, etc

    # Margem média (usa repasses_shopee + repasses_ml)
    df_shopee = query_dataframe("""
        SELECT "Valor do Repasse", "Total da Venda"
        FROM repasses_shopee
        WHERE "Total da Venda" > 0
    """)
    df_ml = query_dataframe("""
        SELECT "Valor do Repasse", "Total da Venda"
        FROM repasses_ml
        WHERE "Total da Venda" > 0
    """)
    repasses = pd.concat([df_shopee, df_ml], ignore_index=True)
    repasses["margem_pct"] = (repasses["Valor do Repasse"] / repasses["Total da Venda"]) * 100
    margem_media = repasses["margem_pct"].mean() if not repasses.empty else 0

    # Previsão hoje (entradas previstas para hoje)
    hoje = datetime.now().strftime("%Y-%m-%d")
    previsao_hoje = df[df["data_venda"].str[:10] == hoje]["valor_total"].sum()

    # ==== CARDS ====
    cards = [
        {"title": "Entradas Totais", "value": f"R$ {total_entradas:,.2f}", "icon": "ri-money-dollar-box-line"},
        {"title": "A Receber", "value": f"R$ {total_pendente:,.2f}", "icon": "ri-timer-line"},
        {"title": "Repasse Shopee", "value": f"R$ {shopee:,.2f}", "icon": "ri-store-2-line"},
        {"title": "Repasse ML", "value": f"R$ {ml:,.2f}", "icon": "ri-shopping-cart-2-line"},
        {"title": "Margem Média", "value": f"{margem_media:.1f}%", "icon": "ri-rocket-2-line"},
        {"title": "Previsão Hoje", "value": f"R$ {previsao_hoje:,.2f}", "icon": "ri-calendar-todo-line"},
    ]

    # ==== GRÁFICO DE EVOLUÇÃO DAS ENTRADAS ====
    # Entradas por dia nos últimos 30 dias
    df["data_venda"] = pd.to_datetime(df["data_venda"], errors="coerce")
    ultimos_30 = df[df["data_venda"] >= (datetime.now() - pd.Timedelta(days=30))]
    serie = ultimos_30.groupby(df["data_venda"].dt.strftime("%d/%m"))["valor_total"].sum().reset_index()
    labels_grafico = serie["data_venda"].tolist()
    valores_entradas = serie["valor_total"].tolist()

    # ==== PIE/DONUT POR CANAL ====
    canais = df["tipo"].str.capitalize().value_counts().index.tolist()
    distrib_canais = df.groupby("tipo")["valor_total"].sum().tolist()

    # ==== ÚLTIMAS ENTRADAS ====
    ultimas = df.sort_values("data_venda", ascending=False).head(12)
    ultimas_entradas = []
    for _, row in ultimas.iterrows():
        ultimas_entradas.append({
            "data": row["data_venda"].strftime("%d/%m/%Y") if pd.notnull(row["data_venda"]) else "",
            "canal": row["tipo"].capitalize(),
            "pedido_id": row.get("pedido_id", ""),
            "valor": f'R$ {row["valor_total"]:,.2f}',
            "status": "Recebido" if row["status"].lower() in ["recebido", "concluido"] else (
                "Pendente" if row["status"].lower() in ["pendente", "a receber", "aguardando"] else row["status"]
            )
        })

    # === CHAMA O TEMPLATE ===
    return render_template(
        "financeiro/entradas_dashboard.html",
        cards=cards,
        labels_grafico=labels_grafico,
        valores_entradas=valores_entradas,
        canais=canais,
        distrib_canais=distrib_canais,
        ultimas_entradas=ultimas_entradas
    )
