"""
Cifrado simétrico Fernet para credenciales sensibles (app passwords de buzón).
La clave se almacena en la variable de entorno ENCRYPTION_KEY.
"""
from cryptography.fernet import Fernet, InvalidToken
from app.core.config import settings


def _fernet() -> Fernet:
    key = settings.ENCRYPTION_KEY
    if not key:
        raise RuntimeError("ENCRYPTION_KEY no está configurada en las variables de entorno")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt(plain: str) -> str:
    """Cifra un texto plano. Retorna token base64 seguro para almacenar en BD."""
    return _fernet().encrypt(plain.encode("utf-8")).decode("utf-8")


def decrypt(token: str) -> str:
    """Descifra un token. Lanza InvalidToken si el token fue alterado o la clave es incorrecta."""
    try:
        return _fernet().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken:
        raise ValueError("No se pudo descifrar la credencial: token inválido o clave incorrecta")
