"""
ANCHOR Key Derivation Module
Argon2id-based key derivation for password-derived keys
"""

import os
import base64
from typing import Tuple

from argon2 import PasswordHasher
from argon2.low_level import hash_secret_raw, Type
import nacl.utils
from nacl.public import PrivateKey

from app.config import get_settings


settings = get_settings()


class KeyDerivation:
    """
    Key derivation utilities using Argon2id.
    
    Argon2id is the recommended algorithm for password hashing and
    key derivation, combining resistance to both side-channel attacks
    (Argon2i) and GPU/ASIC attacks (Argon2d).
    
    Key hierarchy:
    - Master Key: Derived from user secret + recovery quorum
    - Envelope Keys: Per-document keys wrapped by master key
    """
    
    def __init__(
        self,
        time_cost: int = None,
        memory_cost: int = None,
        parallelism: int = None,
        hash_len: int = None,
        salt_len: int = None,
    ):
        """
        Initialize key derivation with Argon2id parameters.
        
        Args:
            time_cost: Number of iterations
            memory_cost: Memory usage in KB
            parallelism: Number of parallel threads
            hash_len: Length of derived key in bytes
            salt_len: Length of salt in bytes
        """
        self.time_cost = time_cost or settings.argon2_time_cost
        self.memory_cost = memory_cost or settings.argon2_memory_cost
        self.parallelism = parallelism or settings.argon2_parallelism
        self.hash_len = hash_len or settings.argon2_hash_len
        self.salt_len = salt_len or settings.argon2_salt_len
        
        # Password hasher for verification
        self.hasher = PasswordHasher(
            time_cost=self.time_cost,
            memory_cost=self.memory_cost,
            parallelism=self.parallelism,
            hash_len=self.hash_len,
            salt_len=self.salt_len,
        )
    
    def generate_salt(self) -> bytes:
        """Generate a cryptographically secure random salt"""
        return os.urandom(self.salt_len)
    
    def derive_key(
        self,
        secret: str | bytes,
        salt: bytes,
        key_length: int = None,
    ) -> bytes:
        """
        Derive a key from a secret using Argon2id.
        
        Args:
            secret: The secret (password, passphrase, or recovery input)
            salt: Random salt (must be stored for key recovery)
            key_length: Length of derived key (defaults to hash_len)
        
        Returns:
            Derived key bytes
        """
        if isinstance(secret, str):
            secret = secret.encode("utf-8")
        
        key_len = key_length or self.hash_len
        
        return hash_secret_raw(
            secret=secret,
            salt=salt,
            time_cost=self.time_cost,
            memory_cost=self.memory_cost,
            parallelism=self.parallelism,
            hash_len=key_len,
            type=Type.ID,  # Argon2id
        )
    
    def derive_key_with_new_salt(
        self,
        secret: str | bytes,
        key_length: int = None,
    ) -> Tuple[bytes, bytes]:
        """
        Derive a key with a newly generated salt.
        
        Returns:
            Tuple of (derived_key, salt)
        """
        salt = self.generate_salt()
        key = self.derive_key(secret, salt, key_length)
        return key, salt
    
    def derive_encryption_key(
        self,
        master_secret: str | bytes,
        salt: bytes,
        context: str = "encryption",
    ) -> bytes:
        """
        Derive an encryption key with context binding.
        
        Uses HKDF-style context binding to derive purpose-specific keys
        from a master secret.
        
        Args:
            master_secret: Master secret or password
            salt: Salt for derivation
            context: Context string for key separation
        
        Returns:
            32-byte encryption key suitable for XChaCha20
        """
        if isinstance(master_secret, str):
            master_secret = master_secret.encode("utf-8")
        
        # Combine secret with context for domain separation
        combined = master_secret + context.encode("utf-8")
        
        return self.derive_key(combined, salt, key_length=32)
    
    def hash_password(self, password: str) -> str:
        """
        Hash a password for storage.
        
        Returns:
            Argon2id hash string (includes salt and parameters)
        """
        return self.hasher.hash(password)
    
    def verify_password(self, hash_string: str, password: str) -> bool:
        """
        Verify a password against a stored hash.
        
        Returns:
            True if password matches, False otherwise
        """
        try:
            self.hasher.verify(hash_string, password)
            return True
        except Exception:
            return False
    
    @staticmethod
    def generate_keypair() -> Tuple[bytes, bytes]:
        """
        Generate an Ed25519/X25519 keypair.
        
        The same keypair can be used for:
        - Ed25519 signatures (identity, attestations)
        - X25519 key exchange (ECDH for encryption)
        
        Returns:
            Tuple of (private_key, public_key) as bytes
        """
        private_key = PrivateKey.generate()
        public_key = private_key.public_key
        
        return bytes(private_key), bytes(public_key)
    
    @staticmethod
    def keypair_to_base64(private_key: bytes, public_key: bytes) -> Tuple[str, str]:
        """
        Encode keypair as base64 strings for storage/transmission.
        
        Returns:
            Tuple of (private_key_b64, public_key_b64)
        """
        return (
            base64.b64encode(private_key).decode("utf-8"),
            base64.b64encode(public_key).decode("utf-8"),
        )
    
    @staticmethod
    def keypair_from_base64(private_key_b64: str, public_key_b64: str) -> Tuple[bytes, bytes]:
        """
        Decode keypair from base64 strings.
        
        Returns:
            Tuple of (private_key, public_key) as bytes
        """
        return (
            base64.b64decode(private_key_b64),
            base64.b64decode(public_key_b64),
        )


# Global instance
key_derivation = KeyDerivation()

