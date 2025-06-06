import os
from dotenv import load_dotenv
import asyncio # Adicionado para o teste com asyncio.run

print("Tentando carregar .env...")
try:
    if load_dotenv():
        print(".env carregado com sucesso.")
    else:
        print("load_dotenv() retornou False. O ficheiro .env pode não ter sido encontrado ou está vazio.")

    # Testar o acesso a uma variável do .env
    api_url_test = os.getenv("API_URL") # Use uma variável que tem no seu .env
    print(f"Valor de API_URL do .env: {api_url_test}")

    # Testar se o asyncio básico funciona
    async def main_test():
        print("Asyncio main_test a executar.")
        await asyncio.sleep(0.1) # Pequena pausa assíncrona
        print("Asyncio main_test concluído.")

    asyncio.run(main_test())

except ImportError as e:
    print(f"Erro de importação: {e}. Verifique se todas as bibliotecas estão instaladas.")
except Exception as e:
    print(f"Ocorreu um erro inesperado: {e}")

print("Script de teste mínimo executado.")