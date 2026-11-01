"""
vault.py — Cryptographic Credential Vault at Rest for CommerceSense AI v3.

Provides:
1. Symmetric encryption/decryption of sensitive credentials at rest (SP-API client secrets,
   LWA refresh tokens, private keys).
2. Authenticated encryption (HMAC-SHA256 + CTR/XOR stream with per-message CSPRNG salt & IV).
   Degrades cleanly across environments without external binary library dependencies.
3. Strict zero-plaintext policy: secret values are never logged or exposed in API responses.
   Only boolean validation flags and masked identifiers (e.g. 'amzn1.oa2-cs.v1.****') are surfaced.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from pathlib import Path
from typing import Optional

VAULT_DIR = Path(os.environ.get("VAULT_DIR") or (Path(__file__).resolve().parent.parent / ".vault"))
KEY_FILE = VAULT_DIR / "master.key"
_CACHED_MASTER_KEY: Optional[bytes] = None


def _get_or_create_master_key() -> bytes:
    """Retrieves or derives the 256-bit vault master key from environment or local keyfile."""
    global _CACHED_MASTER_KEY
    if _CACHED_MASTER_KEY is not None:
        return _CACHED_MASTER_KEY

    env_key = os.environ.get("COMMERCESENSE_VAULT_KEY") or os.environ.get("APP_SECRET_KEY")
    if env_key:
        _CACHED_MASTER_KEY = hashlib.sha256(env_key.encode("utf-8")).digest()
        return _CACHED_MASTER_KEY

    VAULT_DIR.mkdir(parents=True, exist_ok=True)
    if KEY_FILE.exists():
        try:
            with open(KEY_FILE, "rb") as f:
                key = f.read().strip()
                if len(key) == 32:
                    _CACHED_MASTER_KEY = key
                    return _CACHED_MASTER_KEY
        except Exception:
            pass

    new_key = secrets.token_bytes(32)
    try:
        with open(KEY_FILE, "wb") as f:
            f.write(new_key)
        try:
            os.chmod(KEY_FILE, 0o600)
        except Exception:
            pass
    except Exception:
        pass
    _CACHED_MASTER_KEY = new_key
    return _CACHED_MASTER_KEY


def _keystream(key: bytes, iv: bytes, length: int) -> bytes:
    """Generates a cryptographically strong deterministic keystream using HMAC-SHA256 in counter mode."""
    stream = bytearray()
    counter = 0
    while len(stream) < length:
        h = hmac.new(key, iv + counter.to_bytes(4, "big"), hashlib.sha256)
        stream.extend(h.digest())
        counter += 1
    return bytes(stream[:length])


def encrypt_secret(plaintext: str) -> str:
    """Encrypts plaintext string with authenticated HMAC-SHA256 CTR stream cipher.
    Format: base64(salt[16] + iv[16] + tag[32] + ciphertext)
    """
    if not plaintext:
        return ""

    master_key = _get_or_create_master_key()
    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(16)

    # Derive message encryption key and MAC key using HKDF-like extract/expand
    enc_key = hmac.new(master_key, salt + b"enc", hashlib.sha256).digest()
    mac_key = hmac.new(master_key, salt + b"mac", hashlib.sha256).digest()

    plain_bytes = plaintext.encode("utf-8")
    ks = _keystream(enc_key, iv, len(plain_bytes))
    ciphertext = bytes(a ^ b for a, b in zip(plain_bytes, ks))

    # Authenticate ciphertext, salt, and iv
    tag = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).digest()

    payload = salt + iv + tag + ciphertext
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decrypt_secret(token: str) -> Optional[str]:
    """Decrypts and authenticates a vault token. Returns None if invalid or corrupted."""
    if not token:
        return None

    try:
        raw = base64.urlsafe_b64decode(token.encode("ascii"))
        if len(raw) < 64:  # 16 + 16 + 32
            return None

        salt = raw[:16]
        iv = raw[16:32]
        expected_tag = raw[32:64]
        ciphertext = raw[64:]

        master_key = _get_or_create_master_key()
        enc_key = hmac.new(master_key, salt + b"enc", hashlib.sha256).digest()
        mac_key = hmac.new(master_key, salt + b"mac", hashlib.sha256).digest()

        # Verify authentication tag in constant time
        computed_tag = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).digest()
        if not hmac.compare_digest(expected_tag, computed_tag):
            return None

        ks = _keystream(enc_key, iv, len(ciphertext))
        plain_bytes = bytes(a ^ b for a, b in zip(ciphertext, ks))
        return plain_bytes.decode("utf-8")
    except Exception:
        return None


def mask_secret(value: Optional[str], visible_chars: int = 4) -> Optional[str]:
    """Masks secret for display, preserving prefix/suffix while never exposing the body."""
    if not value:
        return None
    val = str(value).strip()
    if len(val) <= visible_chars * 2:
        return "********"
    return f"{val[:visible_chars]}....{val[-visible_chars:]}"
