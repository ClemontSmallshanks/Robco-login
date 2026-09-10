import sys
import base64

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives import padding
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes


def get_machine_id() -> str:
    """Read the Linux system's unique machine ID."""
    with open("/etc/machine-id", "r") as f:
        return f.read().strip()


def derive_key(password: str, salt: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=390000,
    )
    return kdf.derive(password.encode())


def encrypt(plaintext: str, salt: bytes, iv: bytes, password: str) -> str:
    key = derive_key(password, salt)

    padder = padding.PKCS7(algorithms.AES.block_size).padder()
    padded_plaintext = padder.update(plaintext.encode()) + padder.finalize()

    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    encryptor = cipher.encryptor()
    ciphertext = encryptor.update(padded_plaintext) + encryptor.finalize()

    return base64.b64encode(ciphertext).decode()


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print(f"Usage: {sys.argv[0]} PASSWORD SALT_HEX IV_HEX")
        sys.exit(1)

    machine_id = get_machine_id()

    password = sys.argv[1]
    salt = bytes.fromhex(sys.argv[2])
    iv = bytes.fromhex(sys.argv[3])

    ENCRYPTED_PASS = encrypt(password, salt, iv, machine_id)
    print(f"{ENCRYPTED_PASS}")