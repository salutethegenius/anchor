"""
ANCHOR Encryption Service
Client-side encryption utilities for zero-knowledge vault
"""

import os
import base64
import json
from typing import Tuple, Optional, Dict, Any
from dataclasses import dataclass

from nacl.secret import SecretBox
from nacl.public import PrivateKey, PublicKey, Box
from nacl.utils import random as nacl_random
import nacl.bindings


@dataclass
class EncryptedPayload:
    """Container for encrypted data with metadata"""
    ciphertext: bytes
    nonce: bytes
    scheme: str
    key_wrap: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            "ciphertext": base64.b64encode(self.ciphertext).decode("utf-8"),
            "nonce": base64.b64encode(self.nonce).decode("utf-8"),
            "scheme": self.scheme,
            "key_wrap": self.key_wrap,
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "EncryptedPayload":
        """Create from dictionary"""
        return cls(
            ciphertext=base64.b64decode(data["ciphertext"]),
            nonce=base64.b64decode(data["nonce"]),
            scheme=data["scheme"],
            key_wrap=data.get("key_wrap"),
        )


class EncryptionService:
    """
    Encryption service for ANCHOR vault.
    
    Implements zero-knowledge encryption where:
    - All encryption happens client-side
    - Server only sees encrypted blobs
    - Keys are derived from user secret + recovery quorum
    
    Supported schemes:
    - XSalsa20-Poly1305 (via NaCl SecretBox) - symmetric encryption
    - X25519 (via NaCl Box) - asymmetric key exchange + encryption
    
    Note: PyNaCl uses XSalsa20 (not XChaCha20), which is equally secure.
    Both use 24-byte nonces and 256-bit keys.
    """
    
    # Scheme identifiers
    SCHEME_SECRETBOX = "XSalsa20-Poly1305"
    SCHEME_BOX = "X25519-XSalsa20-Poly1305"
    
    @classmethod
    def generate_key(cls) -> bytes:
        """
        Generate a random 32-byte symmetric encryption key.
        
        Returns:
            32-byte key suitable for SecretBox
        """
        return nacl_random(SecretBox.KEY_SIZE)
    
    @classmethod
    def generate_nonce(cls) -> bytes:
        """
        Generate a random 24-byte nonce.
        
        Returns:
            24-byte nonce for XSalsa20
        """
        return nacl_random(SecretBox.NONCE_SIZE)
    
    @classmethod
    def encrypt_symmetric(
        cls,
        plaintext: bytes,
        key: bytes,
        nonce: bytes = None,
    ) -> EncryptedPayload:
        """
        Encrypt data with a symmetric key using XSalsa20-Poly1305.
        
        Args:
            plaintext: Data to encrypt
            key: 32-byte symmetric key
            nonce: Optional 24-byte nonce (generated if not provided)
        
        Returns:
            EncryptedPayload with ciphertext and metadata
        """
        if nonce is None:
            nonce = cls.generate_nonce()
        
        box = SecretBox(key)
        ciphertext = box.encrypt(plaintext, nonce=nonce).ciphertext
        
        return EncryptedPayload(
            ciphertext=ciphertext,
            nonce=nonce,
            scheme=cls.SCHEME_SECRETBOX,
        )
    
    @classmethod
    def decrypt_symmetric(
        cls,
        payload: EncryptedPayload,
        key: bytes,
    ) -> bytes:
        """
        Decrypt data with a symmetric key.
        
        Args:
            payload: EncryptedPayload containing ciphertext and nonce
            key: 32-byte symmetric key
        
        Returns:
            Decrypted plaintext bytes
        """
        box = SecretBox(key)
        return box.decrypt(payload.ciphertext, nonce=payload.nonce)
    
    @classmethod
    def encrypt_asymmetric(
        cls,
        plaintext: bytes,
        recipient_public_key: bytes,
        sender_private_key: bytes = None,
    ) -> EncryptedPayload:
        """
        Encrypt data for a recipient using X25519 key exchange.
        
        If sender_private_key is not provided, an ephemeral keypair
        is generated (recommended for most uses).
        
        Args:
            plaintext: Data to encrypt
            recipient_public_key: Recipient's X25519 public key
            sender_private_key: Optional sender's private key
        
        Returns:
            EncryptedPayload with ciphertext, nonce, and key wrap info
        """
        # Generate ephemeral keypair if sender key not provided
        if sender_private_key is None:
            sender_key = PrivateKey.generate()
            ephemeral = True
        else:
            sender_key = PrivateKey(sender_private_key)
            ephemeral = False
        
        recipient_key = PublicKey(recipient_public_key)
        
        # Create encrypted box
        box = Box(sender_key, recipient_key)
        nonce = cls.generate_nonce()
        ciphertext = box.encrypt(plaintext, nonce=nonce).ciphertext
        
        # Key wrap info for decryption
        key_wrap = {
            "algorithm": "X25519-HKDF",
            "ephemeral": ephemeral,
            "sender_pubkey": base64.b64encode(bytes(sender_key.public_key)).decode("utf-8"),
        }
        
        return EncryptedPayload(
            ciphertext=ciphertext,
            nonce=nonce,
            scheme=cls.SCHEME_BOX,
            key_wrap=key_wrap,
        )
    
    @classmethod
    def decrypt_asymmetric(
        cls,
        payload: EncryptedPayload,
        recipient_private_key: bytes,
        sender_public_key: bytes = None,
    ) -> bytes:
        """
        Decrypt data encrypted with X25519 key exchange.
        
        Args:
            payload: EncryptedPayload with key_wrap info
            recipient_private_key: Recipient's X25519 private key
            sender_public_key: Optional sender's public key (extracted from key_wrap if not provided)
        
        Returns:
            Decrypted plaintext bytes
        """
        if sender_public_key is None:
            if payload.key_wrap is None or "sender_pubkey" not in payload.key_wrap:
                raise ValueError("Sender public key required for decryption")
            sender_public_key = base64.b64decode(payload.key_wrap["sender_pubkey"])
        
        recipient_key = PrivateKey(recipient_private_key)
        sender_key = PublicKey(sender_public_key)
        
        box = Box(recipient_key, sender_key)
        return box.decrypt(payload.ciphertext, nonce=payload.nonce)
    
    @classmethod
    def encrypt_for_vault(
        cls,
        plaintext: bytes,
        document_key: bytes,
    ) -> Tuple[bytes, dict]:
        """
        Encrypt a document for vault storage.
        
        This is the primary method for encrypting vault documents.
        Uses envelope encryption:
        1. Generate a random data encryption key (DEK)
        2. Encrypt the document with the DEK
        3. Encrypt the DEK with the document key
        
        Args:
            plaintext: Document content to encrypt
            document_key: Key for wrapping the DEK
        
        Returns:
            Tuple of (encrypted_blob, encryption_meta)
        """
        # Generate data encryption key
        dek = cls.generate_key()
        
        # Encrypt document with DEK
        payload = cls.encrypt_symmetric(plaintext, dek)
        
        # Wrap DEK with document key
        dek_nonce = cls.generate_nonce()
        dek_box = SecretBox(document_key)
        wrapped_dek = dek_box.encrypt(dek, nonce=dek_nonce).ciphertext
        
        # Combine into blob
        blob = payload.ciphertext
        
        # Encryption metadata
        encryption_meta = {
            "scheme": payload.scheme,
            "nonce": base64.b64encode(payload.nonce).decode("utf-8"),
            "key_wrap": {
                "algorithm": "XSalsa20-Poly1305",
                "wrapped_key": base64.b64encode(wrapped_dek).decode("utf-8"),
                "wrap_nonce": base64.b64encode(dek_nonce).decode("utf-8"),
            }
        }
        
        return blob, encryption_meta
    
    @classmethod
    def decrypt_from_vault(
        cls,
        encrypted_blob: bytes,
        encryption_meta: dict,
        document_key: bytes,
    ) -> bytes:
        """
        Decrypt a document from vault storage.
        
        Args:
            encrypted_blob: Encrypted document content
            encryption_meta: Encryption metadata with key wrap info
            document_key: Key for unwrapping the DEK
        
        Returns:
            Decrypted document bytes
        """
        # Unwrap DEK
        wrapped_dek = base64.b64decode(encryption_meta["key_wrap"]["wrapped_key"])
        wrap_nonce = base64.b64decode(encryption_meta["key_wrap"]["wrap_nonce"])
        
        dek_box = SecretBox(document_key)
        dek = dek_box.decrypt(wrapped_dek, nonce=wrap_nonce)
        
        # Decrypt document
        nonce = base64.b64decode(encryption_meta["nonce"])
        payload = EncryptedPayload(
            ciphertext=encrypted_blob,
            nonce=nonce,
            scheme=encryption_meta["scheme"],
        )
        
        return cls.decrypt_symmetric(payload, dek)
    
    @classmethod
    def generate_content_hash(cls, content: bytes) -> str:
        """
        Generate SHA-256 hash of content for integrity verification.
        
        Args:
            content: Content to hash (typically encrypted blob)
        
        Returns:
            Hex-encoded SHA-256 hash
        """
        import hashlib
        return hashlib.sha256(content).hexdigest()


# Convenience instances
encryption_service = EncryptionService()

