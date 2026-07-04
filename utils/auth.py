import hashlib
import os


def hash_password(password: str) -> str:
    salt = os.urandom(32)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return salt.hex() + ":" + key.hex()


def verify_password(password: str, stored_hash: str) -> bool:
    if not stored_hash or ":" not in stored_hash:
        return False
    salt_hex, key_hex = stored_hash.split(":")
    try:
        salt = bytes.fromhex(salt_hex)
        stored_key = bytes.fromhex(key_hex)
    except (ValueError, TypeError):
        return False
    new_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return new_key == stored_key
