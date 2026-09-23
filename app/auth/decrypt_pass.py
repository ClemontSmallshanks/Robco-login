import os
import json
import base64
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

def decrypt_credential(cred_path: str, machine_id: str) -> str:
    """Strictly validate and decrypt the system password from the secure credentials file."""
    if not os.path.exists(cred_path):
        raise RuntimeError("Credentials file missing.")

    with open(cred_path, "r") as f:
        try:
            enc_data = json.load(f)
        except json.JSONDecodeError:
            raise RuntimeError("Malformed JSON in credentials file.")

    if not isinstance(enc_data, dict):
        raise RuntimeError("Invalid credential structure.")

    version = enc_data.get("version")
    if version != 1:
        raise RuntimeError("Unsupported or missing credential version.")

    try:
        salt = base64.b64decode(enc_data.get("salt", ""), validate=True)
        nonce = base64.b64decode(enc_data.get("nonce", ""), validate=True)
        ciphertext = base64.b64decode(enc_data.get("ciphertext", ""), validate=True)
    except (TypeError, ValueError):
        raise RuntimeError("Missing fields or invalid base64 in credentials.")

    if len(salt) != 16:
        raise RuntimeError("Invalid salt length.")
    if len(nonce) != 12:
        raise RuntimeError("Invalid nonce length.")
    if len(ciphertext) < 16:
        raise RuntimeError("Ciphertext truncated or missing GCM tag.")

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    key = kdf.derive(machine_id.encode('utf-8'))

    aesgcm = AESGCM(key)
    try:
        plaintext = aesgcm.decrypt(nonce, ciphertext, None)
        return plaintext.decode('utf-8')
    except Exception:
        raise RuntimeError("Decryption or authentication failed.")
