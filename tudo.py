import sqlite3
import pandas as pd

conn = sqlite3.connect(DB_PATH)
df = pd.read_sql("SELECT * FROM entradas_financeiras", conn)
conn.close()
print(df.head(10))
print("Soma total:", df['valor'].sum())
print("Soma Shopee:", df[df['canal']=='Shopee']['valor'].sum())
