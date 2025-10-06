import socket
import os

# Pega o host e a porta do .env
DB_HOST = os.getenv("DB_HOST", "dpg-d3hj6iffte5s73d08ovg-a")
DB_PORT = int(os.getenv("DB_PORT", 5432))

try:
    with socket.create_connection((DB_HOST, DB_PORT), timeout=5) as sock:
        print(f"✅ Conexão bem-sucedida: {DB_HOST}:{DB_PORT} está acessível!")
except Exception as e:
    print(f"❌ Não foi possível conectar: {e}")
