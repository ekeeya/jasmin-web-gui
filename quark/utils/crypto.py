#  Copyright (c) 2026
#
"""Encrypt / decrypt workspace Jasmin credentials at rest."""
from __future__ import annotations

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured


class CredentialsKeyError(ImproperlyConfigured):
    """Raised when JOYCE_CREDENTIALS_KEY is missing or invalid."""


def _fernet():
    from cryptography.fernet import Fernet, InvalidToken

    key = getattr(settings, "JOYCE_CREDENTIALS_KEY", "") or ""
    if not key:
        raise CredentialsKeyError(
            "JOYCE_CREDENTIALS_KEY is not set. Generate one with: "
            "python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
        )
    try:
        return Fernet(key.encode("utf-8") if isinstance(key, str) else key)
    except Exception as exc:
        raise CredentialsKeyError(f"Invalid JOYCE_CREDENTIALS_KEY: {exc}") from exc


def encrypt_secret(plaintext: str | None) -> str:
    """Encrypt a secret for DB storage. Empty/None stays empty."""
    if plaintext is None or plaintext == "":
        return ""
    token = _fernet().encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_secret(ciphertext: str | None) -> str:
    """Decrypt a secret loaded from the DB. Empty/None stays empty."""
    if ciphertext is None or ciphertext == "":
        return ""
    from cryptography.fernet import InvalidToken

    try:
        return _fernet().decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise CredentialsKeyError(
            "Could not decrypt stored Jasmin credential. "
            "JOYCE_CREDENTIALS_KEY may have changed."
        ) from exc


def looks_encrypted(value: str | None) -> bool:
    """Heuristic: Fernet tokens are url-safe base64 starting with gAAAAA."""
    if not value:
        return False
    return value.startswith("gAAAAA")
