"""Password hashing with bcrypt directly.

passlib 1.7.4 is unmaintained and incompatible with bcrypt>=4.1 (it reads the
removed ``bcrypt.__about__``); bcrypt 5.x breaks it entirely. Hashes produced
by passlib (``$2b$``) verify fine with ``bcrypt.checkpw``, so existing
passwords keep working.
"""

from __future__ import annotations

import bcrypt as _bcrypt

#: bcrypt only uses the first 72 bytes. Truncating explicitly reproduces the
#: legacy passlib behavior (silent truncation), so pre-migration ``$2b$``
#: hashes keep verifying. (Refresh tokens are ~300-char JWTs.)
_MAX_SECRET_BYTES = 72


def _norm(secret: str) -> bytes:
    raw = secret.encode("utf-8")
    return raw[:_MAX_SECRET_BYTES]


def hash_password(password: str) -> str:
    """Hash a password, returning the ``$2b$`` string."""
    return _bcrypt.hashpw(_norm(password), _bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against a hash. Unverifiable inputs fail closed."""
    try:
        return _bcrypt.checkpw(_norm(password), password_hash.encode("utf-8"))
    except ValueError:
        # Malformed stored hash — treat as non-matching, not a 500.
        return False
