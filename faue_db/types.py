"""Column types for encrypted values and blind indexes.

Convention: encrypted columns end in `_enc`, blind indexes in `_bidx`. The
linter checks both, so an unencrypted sensitive column is a failing build rather
than a review comment somebody missed.
"""

from __future__ import annotations

from sqlalchemy import LargeBinary, String, TypeDecorator


class EncryptedStr(TypeDecorator):
    """Envelope-encrypted text. Ciphertext at rest; plaintext never stored."""

    impl = LargeBinary
    cache_ok = True

    def process_bind_param(self, value, dialect):  # noqa: ANN001, ANN201
        if value is None:
            return None
        from faue_core.crypto import get_encryptor

        return get_encryptor().encrypt(value)

    def process_result_value(self, value, dialect):  # noqa: ANN001, ANN201
        if value is None:
            return None
        from faue_core.crypto import get_encryptor

        return get_encryptor().decrypt(bytes(value))


class BlindIndex(TypeDecorator):
    """HMAC of a normalised value, so equality lookups on encrypted columns stay
    index scans without storing plaintext."""

    impl = String(64)
    cache_ok = True
