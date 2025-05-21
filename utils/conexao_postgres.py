import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()  # Carrega variáveis do .env

def get_db_connection():
    DATABASE_URL = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(DATABASE_URL)
    return conn
