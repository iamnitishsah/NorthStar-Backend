import hashlib
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    sha = hashlib.sha256(password.encode()).hexdigest()
    return pwd_context.hash(sha)


def verify_password(plain_password: str, stored_hash: str) -> bool:
    sha = hashlib.sha256(plain_password.encode()).hexdigest()
    return pwd_context.verify(sha, stored_hash)