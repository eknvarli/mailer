from cryptography.fernet import Fernet
import os
from core.config import settings

FERNET_KEY = os.getenv("FERNET_KEY")
fernet = Fernet(settings.FERNET_KEY.encode())

def encrypt_secret(secret: str) -> str:
    return fernet.encrypt(secret.encode()).decode()

def decrypt_secret(token: str) -> str:
    return fernet.decrypt(token.encode()).decode()
