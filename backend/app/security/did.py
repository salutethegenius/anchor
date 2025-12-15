"""
ANCHOR DID (Decentralized Identifier) Module
Generate and manage DIDs using the did:key method
"""

import base64
import hashlib
from typing import Tuple, Optional

from nacl.signing import SigningKey, VerifyKey
from nacl.encoding import RawEncoder
import nacl.bindings


# Multicodec prefixes for did:key
# Ed25519 public key prefix: 0xed01
ED25519_MULTICODEC_PREFIX = bytes([0xed, 0x01])


class DIDGenerator:
    """
    DID (Decentralized Identifier) generator using did:key method.
    
    did:key is a self-certifying DID method that encodes a public key
    directly in the identifier. This provides:
    - No external resolution required
    - Instant creation without network calls
    - Perfect for W3C Verifiable Credentials
    
    Format: did:key:<multibase-encoded-multicodec-public-key>
    
    For Ed25519: did:key:z6Mk...
    The 'z' prefix indicates base58btc encoding.
    """
    
    # Base58 Bitcoin alphabet
    BASE58_ALPHABET = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
    
    @classmethod
    def generate_keypair(cls) -> Tuple[bytes, bytes]:
        """
        Generate a new Ed25519 keypair.
        
        Returns:
            Tuple of (signing_key_bytes, verify_key_bytes)
            The verify_key (public key) is used for DID generation.
        """
        signing_key = SigningKey.generate()
        verify_key = signing_key.verify_key
        
        return bytes(signing_key), bytes(verify_key)
    
    @classmethod
    def base58_encode(cls, data: bytes) -> str:
        """
        Encode bytes to base58btc (Bitcoin alphabet).
        
        This is the multibase encoding used by did:key with 'z' prefix.
        """
        num = int.from_bytes(data, "big")
        
        if num == 0:
            return cls.BASE58_ALPHABET[0]
        
        result = []
        while num:
            num, remainder = divmod(num, 58)
            result.append(cls.BASE58_ALPHABET[remainder])
        
        # Handle leading zeros
        for byte in data:
            if byte == 0:
                result.append(cls.BASE58_ALPHABET[0])
            else:
                break
        
        return "".join(reversed(result))
    
    @classmethod
    def base58_decode(cls, encoded: str) -> bytes:
        """
        Decode base58btc string to bytes.
        """
        if not encoded:
            return b""
        
        num = 0
        for char in encoded:
            if char not in cls.BASE58_ALPHABET:
                raise ValueError(f"Invalid base58 character: {char}")
            num = num * 58 + cls.BASE58_ALPHABET.index(char)
        
        # Handle leading zeros (1s in base58)
        leading_zeros = 0
        for char in encoded:
            if char == cls.BASE58_ALPHABET[0]:
                leading_zeros += 1
            else:
                break
        
        # Convert number to bytes
        if num == 0:
            return bytes(leading_zeros)
        
        # Determine byte length
        byte_length = (num.bit_length() + 7) // 8
        
        return bytes(leading_zeros) + num.to_bytes(byte_length, "big")
    
    @classmethod
    def public_key_to_did(cls, public_key: bytes) -> str:
        """
        Convert an Ed25519 public key to a did:key identifier.
        
        Args:
            public_key: 32-byte Ed25519 public key
        
        Returns:
            DID string in format: did:key:z6Mk...
        """
        if len(public_key) != 32:
            raise ValueError("Ed25519 public key must be 32 bytes")
        
        # Prepend multicodec prefix
        multicodec_key = ED25519_MULTICODEC_PREFIX + public_key
        
        # Encode with base58btc (multibase 'z' prefix)
        encoded = cls.base58_encode(multicodec_key)
        
        return f"did:key:z{encoded}"
    
    @classmethod
    def did_to_public_key(cls, did: str) -> bytes:
        """
        Extract the public key from a did:key identifier.
        
        Args:
            did: DID string in format: did:key:z6Mk...
        
        Returns:
            32-byte Ed25519 public key
        """
        if not did.startswith("did:key:z"):
            raise ValueError("Invalid did:key format - must start with 'did:key:z'")
        
        # Remove prefix and decode
        encoded = did[9:]  # Remove "did:key:z"
        decoded = cls.base58_decode(encoded)
        
        # Verify multicodec prefix and extract key
        if not decoded.startswith(ED25519_MULTICODEC_PREFIX):
            raise ValueError("Invalid multicodec prefix - expected Ed25519")
        
        public_key = decoded[2:]  # Remove 2-byte prefix
        
        if len(public_key) != 32:
            raise ValueError("Invalid public key length")
        
        return public_key
    
    @classmethod
    def generate_did(cls) -> Tuple[str, bytes, bytes]:
        """
        Generate a new DID with associated keypair.
        
        Returns:
            Tuple of (did_string, signing_key_bytes, verify_key_bytes)
        """
        signing_key, verify_key = cls.generate_keypair()
        did = cls.public_key_to_did(verify_key)
        
        return did, signing_key, verify_key
    
    @classmethod
    def create_verification_method(cls, did: str) -> str:
        """
        Create a verification method URL for the DID.
        
        For did:key, the verification method is the DID itself appended
        with a fragment that is the same as the method-specific identifier.
        
        Example: did:key:z6Mk...#z6Mk...
        """
        method_id = did.split(":")[-1]  # Get z6Mk... part
        return f"{did}#{method_id}"
    
    @classmethod
    def sign_message(cls, message: bytes, signing_key: bytes) -> bytes:
        """
        Sign a message with an Ed25519 signing key.
        
        Args:
            message: Message bytes to sign
            signing_key: 32-byte Ed25519 signing key
        
        Returns:
            64-byte signature
        """
        key = SigningKey(signing_key)
        signed = key.sign(message, encoder=RawEncoder)
        return signed.signature
    
    @classmethod
    def verify_signature(
        cls,
        message: bytes,
        signature: bytes,
        public_key: bytes,
    ) -> bool:
        """
        Verify a signature with an Ed25519 public key.
        
        Args:
            message: Original message bytes
            signature: 64-byte signature
            public_key: 32-byte Ed25519 public key
        
        Returns:
            True if signature is valid
        """
        try:
            verify_key = VerifyKey(public_key)
            verify_key.verify(message, signature)
            return True
        except Exception:
            return False
    
    @classmethod
    def sign_message_base64(
        cls,
        message: str | bytes,
        signing_key: bytes,
    ) -> str:
        """
        Sign a message and return base64-encoded signature.
        
        Args:
            message: Message to sign (string or bytes)
            signing_key: 32-byte Ed25519 signing key
        
        Returns:
            Base64-encoded signature
        """
        if isinstance(message, str):
            message = message.encode("utf-8")
        
        signature = cls.sign_message(message, signing_key)
        return base64.b64encode(signature).decode("utf-8")
    
    @classmethod
    def verify_signature_base64(
        cls,
        message: str | bytes,
        signature_b64: str,
        public_key: bytes,
    ) -> bool:
        """
        Verify a base64-encoded signature.
        
        Args:
            message: Original message (string or bytes)
            signature_b64: Base64-encoded signature
            public_key: 32-byte Ed25519 public key
        
        Returns:
            True if signature is valid
        """
        if isinstance(message, str):
            message = message.encode("utf-8")
        
        try:
            signature = base64.b64decode(signature_b64)
            return cls.verify_signature(message, signature, public_key)
        except Exception:
            return False


# Convenience functions
def generate_did() -> Tuple[str, bytes, bytes]:
    """Generate a new DID with keypair"""
    return DIDGenerator.generate_did()


def public_key_to_did(public_key: bytes) -> str:
    """Convert public key to DID"""
    return DIDGenerator.public_key_to_did(public_key)


def did_to_public_key(did: str) -> bytes:
    """Extract public key from DID"""
    return DIDGenerator.did_to_public_key(did)

