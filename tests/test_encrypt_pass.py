import os
import json
import base64
import pytest

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from app.auth.encrypt_pass import encrypt, derive_key
    from app.auth.decrypt_pass import decrypt_credential
except ImportError:
    pass # cryptography is likely in the venv

MOCK_MACHINE_ID = "test-machine-id-1234567890abcdef"
TEST_PASSWORD = "correct-horse-battery-staple"

def test_encrypt_then_decrypt_returns_original(tmp_path):
    """TEST 1: Encrypt then decrypt returns exactly the original password."""
    enc_data = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    plaintext = decrypt_credential(str(cred_file), MOCK_MACHINE_ID)
    assert plaintext == TEST_PASSWORD

def test_different_encryptions_produce_different_results():
    """TEST 2: Two encryptions of the same password produce different encrypted results."""
    enc1 = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    enc2 = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    
    assert enc1["salt"] != enc2["salt"]
    assert enc1["nonce"] != enc2["nonce"]
    assert enc1["ciphertext"] != enc2["ciphertext"]

def test_changing_ciphertext_causes_failure(tmp_path):
    """TEST 3 & J: Changing the ciphertext causes decryption/authentication failure."""
    enc_data = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    ciphertext = bytearray(base64.b64decode(enc_data["ciphertext"]))
    ciphertext[0] ^= 0x01
    enc_data["ciphertext"] = base64.b64encode(ciphertext).decode('utf-8')
    
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    with pytest.raises(RuntimeError, match="Decryption or authentication failed"):
        decrypt_credential(str(cred_file), MOCK_MACHINE_ID)

def test_changing_auth_tag_causes_failure(tmp_path):
    """TEST 4: Changing the authentication tag causes failure."""
    enc_data = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    ciphertext = bytearray(base64.b64decode(enc_data["ciphertext"]))
    ciphertext[-1] ^= 0x01
    enc_data["ciphertext"] = base64.b64encode(ciphertext).decode('utf-8')
    
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    with pytest.raises(RuntimeError, match="Decryption or authentication failed"):
        decrypt_credential(str(cred_file), MOCK_MACHINE_ID)

def test_different_machine_id_cannot_decrypt(tmp_path):
    """TEST 5 & K: Using a different machine-id-derived key cannot decrypt."""
    enc_data = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    with pytest.raises(RuntimeError, match="Decryption or authentication failed"):
        decrypt_credential(str(cred_file), "wrong-machine-id")

def test_malformed_credential_data_fails_cleanly(tmp_path):
    """TEST 6 & D: Invalid Base64."""
    enc_data = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    enc_data["salt"] = "!!!" # Invalid base64
    
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    with pytest.raises(RuntimeError, match="Missing fields or invalid base64"):
        decrypt_credential(str(cred_file), MOCK_MACHINE_ID)

def test_unsupported_version_rejected(tmp_path):
    """TEST B & C: Missing or unsupported version is rejected."""
    enc_data = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    enc_data["version"] = 99
    
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    with pytest.raises(RuntimeError, match="Unsupported or missing credential version"):
        decrypt_credential(str(cred_file), MOCK_MACHINE_ID)
        
    del enc_data["version"]
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    with pytest.raises(RuntimeError, match="Unsupported or missing credential version"):
        decrypt_credential(str(cred_file), MOCK_MACHINE_ID)

def test_malformed_json_fails(tmp_path):
    """TEST E: Malformed JSON."""
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        f.write("{invalid_json: true")
        
    with pytest.raises(RuntimeError, match="Malformed JSON"):
        decrypt_credential(str(cred_file), MOCK_MACHINE_ID)

def test_missing_salt_fails(tmp_path):
    """TEST F: Missing salt."""
    enc_data = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    del enc_data["salt"]
    
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    with pytest.raises(RuntimeError, match="Invalid salt length"):
        decrypt_credential(str(cred_file), MOCK_MACHINE_ID)

def test_wrong_salt_length_fails(tmp_path):
    """TEST G: Wrong salt length."""
    enc_data = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    enc_data["salt"] = base64.b64encode(os.urandom(8)).decode('utf-8')
    
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    with pytest.raises(RuntimeError, match="Invalid salt length"):
        decrypt_credential(str(cred_file), MOCK_MACHINE_ID)

def test_wrong_nonce_length_fails(tmp_path):
    """TEST H: Wrong nonce length."""
    enc_data = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    enc_data["nonce"] = base64.b64encode(os.urandom(10)).decode('utf-8')
    
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    with pytest.raises(RuntimeError, match="Invalid nonce length"):
        decrypt_credential(str(cred_file), MOCK_MACHINE_ID)

def test_truncated_ciphertext_fails(tmp_path):
    """TEST I: Truncated ciphertext."""
    enc_data = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    enc_data["ciphertext"] = base64.b64encode(os.urandom(10)).decode('utf-8') # Less than 16 bytes auth tag
    
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    with pytest.raises(RuntimeError, match="Ciphertext truncated or missing GCM tag"):
        decrypt_credential(str(cred_file), MOCK_MACHINE_ID)

def test_empty_password(tmp_path):
    """TEST 7: Empty-password behavior."""
    enc_data = encrypt("", MOCK_MACHINE_ID)
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    plaintext = decrypt_credential(str(cred_file), MOCK_MACHINE_ID)
    assert plaintext == ""

def test_unicode_passwords_work(tmp_path):
    """TEST 8 & M: Unicode passwords work correctly."""
    pwd = "🔐 Hello, 世界! パスワード 🔐"
    enc_data = encrypt(pwd, MOCK_MACHINE_ID)
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    plaintext = decrypt_credential(str(cred_file), MOCK_MACHINE_ID)
    assert plaintext == pwd

def test_long_passwords_work(tmp_path):
    """TEST 9 & N: Long passwords work correctly."""
    pwd = "TestPassword123!" * 100
    enc_data = encrypt(pwd, MOCK_MACHINE_ID)
    cred_file = tmp_path / "credentials.enc"
    with open(cred_file, "w") as f:
        json.dump(enc_data, f)
        
    plaintext = decrypt_credential(str(cred_file), MOCK_MACHINE_ID)
    assert plaintext == pwd

def test_no_plaintext_in_encrypted_representation():
    """TEST 10 & O: The encrypted representation contains no plaintext password."""
    enc_data = encrypt(TEST_PASSWORD, MOCK_MACHINE_ID)
    assert TEST_PASSWORD not in str(enc_data)
    ciphertext = base64.b64decode(enc_data["ciphertext"])
    assert TEST_PASSWORD.encode('utf-8') not in ciphertext
