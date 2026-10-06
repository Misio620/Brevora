from cryptography.fernet import Fernet

from app.config import get_settings

settings = get_settings()


def _get_fernet() -> Fernet | None:
    if not settings.ENCRYPTION_KEY:
        return None
    return Fernet(settings.ENCRYPTION_KEY.encode())


def encrypt_token(token: str) -> str:
    f = _get_fernet()
    if not f:
        # Never store OAuth tokens in plain text; the API refuses to start without a key
        raise RuntimeError("ENCRYPTION_KEY is not configured")
    return f.encrypt(token.encode()).decode()


def decrypt_token(encrypted: str) -> str:
    f = _get_fernet()
    if not f:
        return encrypted
    try:
        return f.decrypt(encrypted.encode()).decode()
    except Exception:
        return encrypted  # Fallback if decryption fails (e.g., migrating from plain)
