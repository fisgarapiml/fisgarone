# atualizar_campos_antigos.py
import os
os.environ["PYTHONIOENCODING"] = "utf-8"

from pyngrok import ngrok


# Porta padrão do Flask
url_publica = ngrok.connect(5000)
print("🔗 URL pública externa:", url_publica)
