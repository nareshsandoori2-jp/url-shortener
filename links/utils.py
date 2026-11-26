import secrets
import string

ALPHABET = string.ascii_letters + string.digits
RESERVED_CODES = {"api", "admin", "static"}


def generate_code(length=6):
    return "".join(secrets.choice(ALPHABET) for _ in range(length))
