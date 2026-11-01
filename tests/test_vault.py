"""
test_vault.py — Verifies authenticated credential encryption at rest and masking.
"""

import pytest
from providers.vault import encrypt_secret, decrypt_secret, mask_secret


def test_encryption_decryption_roundtrip():
    secret = "amzn1.oa2-cs.v1.2b591b9380f769df8b44983efb1c2d"
    token = encrypt_secret(secret)
    assert token != secret
    assert len(token) > len(secret)

    decrypted = decrypt_secret(token)
    assert decrypted == secret


def test_tamper_proofing():
    secret = "super_confidential_lwa_refresh_token"
    token = encrypt_secret(secret)

    # Tamper with the token
    raw = bytearray(token.encode("ascii"))
    raw[20] = (raw[20] + 1) % 256
    tampered = raw.decode("ascii", errors="ignore")

    # Decryption must fail and return None
    assert decrypt_secret(tampered) is None


def test_mask_secret():
    assert mask_secret(None) is None
    assert mask_secret("short") == "********"
    masked = mask_secret("amzn1.oa2-cs.v1.abcdef1234567890", visible_chars=4)
    assert masked.startswith("amzn")
    assert masked.endswith("7890")
    assert "abcdef" not in masked

