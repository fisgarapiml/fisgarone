import sqlite3

DB_PATH = 'grupo_fisgar.db'

def corrigir_produtos_processados(db_path=DB_PATH):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    atualizados = 0
    pulados = []

    # Busca todos os produtos com custo_unitario ou custo_com_ipi nulo ou zero
    cur.execute("""
        SELECT codigo, qtd_volumes, qtd_por_volume, valor_total, ipi
        FROM produtos_processados
        WHERE 
            custo_unitario IS NULL OR custo_unitario = 0
            OR custo_com_ipi IS NULL OR custo_com_ipi = 0
    """)

    for row in cur.fetchall():
        codigo, qtd_volumes, qtd_por_volume, valor_total, ipi = row

        try:
            qtd_volumes = int(qtd_volumes) if qtd_volumes is not None else 0
            qtd_por_volume = int(qtd_por_volume) if qtd_por_volume is not None else 0
            valor_total = float(valor_total) if valor_total is not None else 0.0
            ipi = float(ipi) if ipi is not None else 0.0
        except Exception as e:
            pulados.append((codigo, f'Conversão de tipo inválida: {e}'))
            continue

        # Não processa casos impossíveis (campos zerados)
        if qtd_volumes <= 0 or qtd_por_volume <= 0 or valor_total <= 0:
            pulados.append((codigo, f'Dados insuficientes (qtd_volumes={qtd_volumes}, qtd_por_volume={qtd_por_volume}, valor_total={valor_total})'))
            continue

        try:
            qtd_real_unidades = qtd_volumes * qtd_por_volume
            custo_volume = valor_total / qtd_volumes
            custo_unitario = custo_volume / qtd_por_volume
            custo_com_ipi = custo_unitario * (1 + ipi / 100.0)
            # Atualiza no banco
            cur.execute("""
                UPDATE produtos_processados
                SET 
                    custo_unitario = ?,
                    custo_com_ipi = ?,
                    qtd_real_unidades = ?
                WHERE codigo = ?
            """, (round(custo_unitario, 6), round(custo_com_ipi, 6), qtd_real_unidades, codigo))
            atualizados += 1
        except Exception as e:
            pulados.append((codigo, f'Erro ao calcular: {e}'))

    conn.commit()
    conn.close()
    print(f"✅ {atualizados} registros corrigidos!")
    if pulados:
        print("⚠️ Registros não atualizados (veja motivo):")
        for codigo, motivo in pulados:
            print(f"- Código {codigo}: {motivo}")

if __name__ == '__main__':
    corrigir_produtos_processados()
