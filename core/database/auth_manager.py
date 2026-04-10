"""PIN authentication management for admin access."""

from __future__ import annotations

import hashlib
import hmac
import os
from typing import Callable


class AuthManager:
    """Manages admin PIN hashing, verification, and legacy migration.

    Args:
        get_parameter_fn: Callable to retrieve a parameter value by key.
        set_parameter_fn: Callable to store a parameter value by key.
    """

    _PIN_ALGO = "pbkdf2_sha256"
    _PIN_ITERATIONS = 200_000

    def __init__(
        self,
        get_parameter_fn: Callable[[str, str | None], str | None],
        set_parameter_fn: Callable[[str, str, str | None], None],
    ) -> None:
        self._get_parameter = get_parameter_fn
        self._set_parameter = set_parameter_fn

    def _hash_admin_pin(self, pin: str, *, salt_hex: str | None = None) -> str:
        salt = bytes.fromhex(salt_hex) if salt_hex else os.urandom(16)
        digest = hashlib.pbkdf2_hmac(
            "sha256",
            pin.encode("utf-8"),
            salt,
            self._PIN_ITERATIONS,
        ).hex()
        return f"{self._PIN_ALGO}${self._PIN_ITERATIONS}${salt.hex()}${digest}"

    def _is_hashed_admin_pin(self, value: str | None) -> bool:
        if not value:
            return False
        parts = str(value).split("$")
        return len(parts) == 4 and parts[0] == self._PIN_ALGO and parts[1].isdigit()

    def _verify_hashed_admin_pin(self, pin: str, stored: str) -> bool:
        try:
            algo, iterations_str, salt_hex, expected_digest = stored.split("$")
            if algo != self._PIN_ALGO:
                return False
            iterations = int(iterations_str)
            digest = hashlib.pbkdf2_hmac(
                "sha256",
                pin.encode("utf-8"),
                bytes.fromhex(salt_hex),
                iterations,
            ).hex()
            return hmac.compare_digest(digest, expected_digest)
        except (ValueError, TypeError):
            return False

    def _normalize_pin(self, pin: str) -> str:
        value = str(pin or "").strip()
        if len(value) < 4 or len(value) > 32:
            raise ValueError("Le code admin doit contenir entre 4 et 32 caracteres.")
        return value

    def ensure_admin_pin_initialized(self) -> None:
        raw = self._get_parameter("ADMIN_PIN")
        if raw is not None:
            return
        self.set_admin_pin("1991")

    def migrate_legacy_admin_pin_if_needed(self) -> None:
        raw = self._get_parameter("ADMIN_PIN")
        if raw is None or self._is_hashed_admin_pin(raw):
            return
        self.set_admin_pin(str(raw))

    def get_admin_pin(self, default: str = "1234") -> str:
        raw = self._get_parameter("ADMIN_PIN")
        if raw is None:
            return str(default)
        raw_str = str(raw)
        if self._is_hashed_admin_pin(raw_str):
            return ""
        return raw_str

    def set_admin_pin(self, pin: str) -> None:
        normalized = self._normalize_pin(pin)
        hashed = self._hash_admin_pin(normalized)
        self._set_parameter(
            "ADMIN_PIN", hashed, "Hash du code admin pour debloquer edition formulaires"
        )

    def verify_admin_pin(self, pin: str) -> bool:
        raw = self._get_parameter("ADMIN_PIN")
        normalized_pin = str(pin or "").strip()
        if raw is None:
            default_pin = self._normalize_pin("1234")
            self.set_admin_pin(default_pin)
            return hmac.compare_digest(normalized_pin, default_pin)

        stored = str(raw)
        if self._is_hashed_admin_pin(stored):
            return self._verify_hashed_admin_pin(normalized_pin, stored)

        # Compatibilite avec anciennes DB en clair: migration apres succes.
        if hmac.compare_digest(normalized_pin, stored.strip()):
            self.set_admin_pin(stored.strip())
            return True
        return False

    def set_user_registration_code(self, operateur_id: int, code: str) -> None:
        """Set registration code for a specific user/operator."""
        normalized = self._normalize_pin(code)
        hashed = self._hash_admin_pin(normalized)
        key = f"USER_REG_CODE_{operateur_id}"
        self._set_parameter(
            key, hashed, f"Hash du code d'enregistrement pour l'operateur {operateur_id}"
        )

    def verify_user_registration_code(self, operateur_id: int, code: str) -> bool:
        """Verify registration code for a specific user/operator."""
        key = f"USER_REG_CODE_{operateur_id}"
        raw = self._get_parameter(key)
        normalized_code = str(code or "").strip()

        if raw is None:
            # Default registration code for new users (same as admin default)
            default_code = self._normalize_pin("1234")
            self.set_user_registration_code(operateur_id, default_code)
            return hmac.compare_digest(normalized_code, default_code)

        stored = str(raw)
        if self._is_hashed_admin_pin(stored):
            return self._verify_hashed_admin_pin(normalized_code, stored)

        # Compatibilite avec anciennes DB en clair: migration apres succes.
        if hmac.compare_digest(normalized_code, stored.strip()):
            self.set_user_registration_code(operateur_id, stored.strip())
            return True
        return False
