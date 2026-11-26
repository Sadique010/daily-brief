import base64, json, os
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

ITER = 600000
DATA = "docs/data"


def _passphrase():
    p = os.environ.get("DAILY_BRIEF_PASSPHRASE")
    if not p and os.path.exists(".env"):
        for line in open(".env", encoding="utf-8"):
            if line.startswith("DAILY_BRIEF_PASSPHRASE="):
                p = line.split("=", 1)[1].strip("\r\n")
    if not p or len(p) < 20:
        raise RuntimeError("DAILY_BRIEF_PASSPHRASE missing or shorter than 20 characters")
    return p


def _salt():
    os.makedirs(DATA, exist_ok=True)
    path = f"{DATA}/salt.txt"
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(base64.b64encode(os.urandom(16)).decode())
    return base64.b64decode(open(path).read().strip())


def get_key():
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=_salt(), iterations=ITER)
    return kdf.derive(_passphrase().encode("utf-8"))


def encrypt_obj(obj, key):
    iv = os.urandom(12)
    ct = AESGCM(key).encrypt(iv, json.dumps(obj, ensure_ascii=False).encode("utf-8"), None)
    return base64.b64encode(iv + ct).decode()


def decrypt_obj(text, key):
    raw = base64.b64decode(text)
    return json.loads(AESGCM(key).decrypt(raw[:12], raw[12:], None).decode("utf-8"))
