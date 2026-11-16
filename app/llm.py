import os

from dotenv import load_dotenv

load_dotenv()  # Se leen las variables del archivo .env (OPENAI_API_KEY, modelos)

CHAT_MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-embedding-3-small")

cliente = None


def get_client():
    # El cliente de OpenAI se crea hasta la primera vez que se usa, así los tests no necesitan la API key
    global cliente
    if cliente is None:
        from openai import OpenAI
        cliente = OpenAI()
    return cliente
