from cryptography.fernet import Fernet
import os
from dotenv import load_dotenv
import json

load_dotenv(override=True)


def encrypt(data):
    if os.environ.get("SECRET_KEY"):
        key = os.environ.get("SECRET_KEY")
        key = bytes(key, "utf-8")
    else:
        key = Fernet.generate_key()
        with open(".env", "a") as f:
            f.write(f'\nSECRET_KEY= "{key.decode()}"')
    fernet = Fernet(key)
    if isinstance(data, dict):
        data = json.dumps(data)
    return fernet.encrypt(data.encode())


def decrypt(data):
    key = os.environ.get("SECRET_KEY")
    key = bytes(key, "utf-8")

    fernet = Fernet(key)
    decrypted_data = fernet.decrypt(data).decode()

    if decrypted_data.startswith("{"):
        decrypted_data = json.loads(decrypted_data)
    return decrypted_data
