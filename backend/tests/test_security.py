"""
Tests for ANCHOR security modules
"""

import pytest
import base64

from app.security.keys import KeyDerivation, key_derivation
from app.security.did import DIDGenerator, generate_did, public_key_to_did
from app.security.encryption import EncryptionService


class TestKeyDerivation:
    """Test Argon2id key derivation"""
    
    def test_generate_salt(self):
        """Salt generation produces correct length"""
        salt = key_derivation.generate_salt()
        assert len(salt) == 16
    
    def test_derive_key(self):
        """Key derivation produces consistent results"""
        secret = "test-password"
        salt = key_derivation.generate_salt()
        
        key1 = key_derivation.derive_key(secret, salt)
        key2 = key_derivation.derive_key(secret, salt)
        
        assert key1 == key2
        assert len(key1) == 32
    
    def test_different_salts_produce_different_keys(self):
        """Different salts produce different keys"""
        secret = "test-password"
        salt1 = key_derivation.generate_salt()
        salt2 = key_derivation.generate_salt()
        
        key1 = key_derivation.derive_key(secret, salt1)
        key2 = key_derivation.derive_key(secret, salt2)
        
        assert key1 != key2
    
    def test_generate_keypair(self):
        """Keypair generation produces valid keys"""
        private_key, public_key = KeyDerivation.generate_keypair()
        
        assert len(private_key) == 32
        assert len(public_key) == 32
    
    def test_password_hashing(self):
        """Password hashing and verification works"""
        password = "secure-password-123"
        
        hash_string = key_derivation.hash_password(password)
        
        assert key_derivation.verify_password(hash_string, password)
        assert not key_derivation.verify_password(hash_string, "wrong-password")


class TestDIDGenerator:
    """Test DID generation and verification"""
    
    def test_generate_did(self):
        """DID generation produces valid format"""
        did, signing_key, verify_key = generate_did()
        
        assert did.startswith("did:key:z")
        assert len(signing_key) == 32
        assert len(verify_key) == 32
    
    def test_public_key_to_did_roundtrip(self):
        """Public key to DID conversion is reversible"""
        _, public_key = DIDGenerator.generate_keypair()
        
        did = public_key_to_did(public_key)
        recovered_key = DIDGenerator.did_to_public_key(did)
        
        assert recovered_key == public_key
    
    def test_sign_and_verify(self):
        """Message signing and verification works"""
        message = b"Hello, ANCHOR!"
        signing_key, verify_key = DIDGenerator.generate_keypair()
        
        signature = DIDGenerator.sign_message(message, signing_key)
        
        assert len(signature) == 64
        assert DIDGenerator.verify_signature(message, signature, verify_key)
    
    def test_sign_and_verify_base64(self):
        """Base64 signing and verification works"""
        message = "Hello, ANCHOR!"
        signing_key, verify_key = DIDGenerator.generate_keypair()
        
        signature_b64 = DIDGenerator.sign_message_base64(message, signing_key)
        
        assert DIDGenerator.verify_signature_base64(message, signature_b64, verify_key)
    
    def test_verification_method(self):
        """Verification method URL is correctly formed"""
        did, _, _ = generate_did()
        
        verification_method = DIDGenerator.create_verification_method(did)
        
        assert verification_method.startswith(did)
        assert "#" in verification_method


class TestEncryptionService:
    """Test encryption utilities"""
    
    def test_generate_key(self):
        """Key generation produces correct length"""
        key = EncryptionService.generate_key()
        assert len(key) == 32
    
    def test_generate_nonce(self):
        """Nonce generation produces correct length"""
        nonce = EncryptionService.generate_nonce()
        assert len(nonce) == 24
    
    def test_symmetric_encryption_roundtrip(self):
        """Symmetric encryption and decryption works"""
        plaintext = b"Secret document content"
        key = EncryptionService.generate_key()
        
        payload = EncryptionService.encrypt_symmetric(plaintext, key)
        decrypted = EncryptionService.decrypt_symmetric(payload, key)
        
        assert decrypted == plaintext
    
    def test_asymmetric_encryption_roundtrip(self):
        """Asymmetric encryption and decryption works"""
        from nacl.public import PrivateKey
        
        plaintext = b"Secret message for recipient"
        
        # Generate recipient keypair
        recipient_private = PrivateKey.generate()
        recipient_public = bytes(recipient_private.public_key)
        
        # Encrypt for recipient
        payload = EncryptionService.encrypt_asymmetric(
            plaintext, 
            recipient_public
        )
        
        # Decrypt as recipient
        decrypted = EncryptionService.decrypt_asymmetric(
            payload,
            bytes(recipient_private)
        )
        
        assert decrypted == plaintext
    
    def test_vault_encryption_roundtrip(self):
        """Vault envelope encryption works"""
        document_content = b"This is a passport document..."
        document_key = EncryptionService.generate_key()
        
        # Encrypt for vault
        encrypted_blob, encryption_meta = EncryptionService.encrypt_for_vault(
            document_content,
            document_key
        )
        
        # Decrypt from vault
        decrypted = EncryptionService.decrypt_from_vault(
            encrypted_blob,
            encryption_meta,
            document_key
        )
        
        assert decrypted == document_content
    
    def test_content_hash(self):
        """Content hash generation works"""
        content = b"Some content to hash"
        
        hash1 = EncryptionService.generate_content_hash(content)
        hash2 = EncryptionService.generate_content_hash(content)
        
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex digest


class TestIntegration:
    """Integration tests for security flow"""
    
    def test_full_account_creation_flow(self):
        """Test complete account creation security flow"""
        # Generate keypair for new account
        did, signing_key, verify_key = generate_did()
        
        # Verify DID format
        assert did.startswith("did:key:z6Mk")  # Ed25519 DIDs start with z6Mk
        
        # Derive encryption key from password
        password = "user-secret-password"
        salt = key_derivation.generate_salt()
        encryption_key = key_derivation.derive_encryption_key(password, salt)
        
        # Encrypt a document
        document = b"My passport data..."
        encrypted_blob, encryption_meta = EncryptionService.encrypt_for_vault(
            document,
            encryption_key
        )
        
        # Verify we can decrypt with same key
        decrypted = EncryptionService.decrypt_from_vault(
            encrypted_blob,
            encryption_meta,
            encryption_key
        )
        
        assert decrypted == document
        
        # Sign a message (for attestation)
        claim = "I verify this document"
        signature = DIDGenerator.sign_message_base64(claim, signing_key)
        
        # Verify signature
        assert DIDGenerator.verify_signature_base64(claim, signature, verify_key)

