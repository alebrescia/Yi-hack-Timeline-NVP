import os
import stat

from cryptography.fernet import Fernet, InvalidToken

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(BASE_DIR, "secret.key")

_PREFIX = "enc:"


def _get_or_create_key():
    if not os.path.exists(KEY_PATH):
        key = Fernet.generate_key()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
        os.chmod(KEY_PATH, stat.S_IRUSR | stat.S_IWUSR)  # 600: solo il proprietario
        return key
    with open(KEY_PATH, "rb") as f:
        return f.read()


def _fernet():
    return Fernet(_get_or_create_key())


def is_encrypted(value):
    return isinstance(value, str) and value.startswith(_PREFIX)


def encrypt(plaintext):
    if not plaintext:
        return plaintext
    token = _fernet().encrypt(plaintext.encode("utf-8")).decode("ascii")
    return _PREFIX + token


def decrypt(value):
    """Decifra se il valore ha il prefisso 'enc:'; altrimenti lo restituisce
    così com'è (compatibilità con password ancora salvate in chiaro)."""
    if not is_encrypted(value):
        return value
    token = value[len(_PREFIX):]
    try:
        return _fernet().decrypt(token.encode("ascii")).decode("utf-8")
    except InvalidToken:
        raise ValueError(
            "Impossibile decifrare una password di config.json: secret.key "
            "non corrisponde (è stato perso, sostituito o copiato da un'altra installazione?)."
        )
