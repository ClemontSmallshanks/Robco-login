import sys
import json
import os
import base64
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

def get_machine_id() -> str:
    """Read the Linux system's unique machine ID."""
    with open("/etc/machine-id", "r") as f:
        return f.read().strip()

def derive_key(machine_id: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    return kdf.derive(machine_id.encode('utf-8'))

def encrypt(plaintext: str, machine_id: str) -> dict:
    salt = os.urandom(16)
    nonce = os.urandom(12)
    key = derive_key(machine_id, salt)

    aesgcm = AESGCM(key)
    ciphertext = aesgcm.encrypt(nonce, plaintext.encode('utf-8'), None)

    return {
        "version": 1,
        "salt": base64.b64encode(salt).decode('utf-8'),
        "nonce": base64.b64encode(nonce).decode('utf-8'),
        "ciphertext": base64.b64encode(ciphertext).decode('utf-8')
    }

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <output_file>", file=sys.stderr)
        sys.exit(1)

    machine_id = get_machine_id()
    # Read password from stdin securely
    password = sys.stdin.read()
    if password.endswith('\n'):
        password = password[:-1]

    if not password:
        print("Error: empty password", file=sys.stderr)
        sys.exit(1)

    out_path = sys.argv[1]
    enc_data = encrypt(password, machine_id)

    # Write output to the destination file
    fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, 'w') as f:
        json.dump(enc_data, f)