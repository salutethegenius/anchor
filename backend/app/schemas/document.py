"""
ANCHOR Document Schemas
Pydantic models for Document API request/response validation
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.document import DocumentType


class EncryptionMeta(BaseModel):
    """Schema for encryption metadata"""
    scheme: str = Field(
        ...,
        description="Encryption scheme (e.g., 'XChaCha20-Poly1305')"
    )
    key_wrap: dict = Field(
        ...,
        description="Key wrapping information"
    )
    nonce: Optional[str] = Field(
        None,
        description="Nonce/IV used for encryption (base64)"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scheme": "XChaCha20-Poly1305",
                "key_wrap": {
                    "algorithm": "X25519-HKDF",
                    "ephemeral_pubkey": "base64-encoded-key"
                },
                "nonce": "base64-encoded-nonce"
            }
        }
    )


class DocumentCreate(BaseModel):
    """
    Schema for storing a new document reference.
    
    The actual document content is encrypted client-side.
    Only the encrypted blob reference is stored on the server.
    Zero-knowledge: server sees metadata, not content.
    """
    doc_type: DocumentType = Field(
        ...,
        description="Type of document"
    )
    display_name_encrypted: Optional[str] = Field(
        None,
        description="Encrypted display name (client-side encryption)"
    )
    ciphertext_ref: str = Field(
        ...,
        description="Reference to encrypted blob in storage (e.g., S3 key)",
        min_length=1
    )
    encryption_meta: dict = Field(
        ...,
        description="Encryption scheme and key wrap information"
    )
    content_hash: Optional[str] = Field(
        None,
        description="SHA-256 hash of encrypted content"
    )
    file_meta: Optional[dict] = Field(
        None,
        description="Encrypted file metadata"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Document expiration date"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "doc_type": "passport",
                "display_name_encrypted": "encrypted-base64-string",
                "ciphertext_ref": "vault/550e8400-e29b-41d4-a716-446655440000/passport-001.enc",
                "encryption_meta": {
                    "scheme": "XChaCha20-Poly1305",
                    "key_wrap": {
                        "algorithm": "X25519-HKDF",
                        "ephemeral_pubkey": "base64-key"
                    },
                    "nonce": "base64-nonce"
                },
                "content_hash": "sha256-hash-of-encrypted-content",
                "expires_at": "2030-01-15T00:00:00Z"
            }
        }
    )


class DocumentResponse(BaseModel):
    """
    Schema for document response.
    Returns document metadata without actual content.
    """
    doc_id: UUID = Field(..., description="Document identifier")
    owner_id: UUID = Field(..., description="Owner account ID")
    doc_type: DocumentType = Field(..., description="Type of document")
    display_name_encrypted: Optional[str] = Field(
        None,
        description="Encrypted display name"
    )
    ciphertext_ref: str = Field(..., description="Reference to encrypted blob")
    encryption_meta: dict = Field(..., description="Encryption metadata")
    content_hash: Optional[str] = Field(None, description="Content integrity hash")
    file_meta: Optional[dict] = Field(None, description="File metadata")
    created_at: datetime = Field(..., description="Upload timestamp")
    updated_at: datetime = Field(..., description="Last modification")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    attestation_count: int = Field(
        default=0,
        description="Number of attestations for this document"
    )
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "doc_id": "660e8400-e29b-41d4-a716-446655440000",
                "owner_id": "550e8400-e29b-41d4-a716-446655440000",
                "doc_type": "passport",
                "ciphertext_ref": "vault/550e8400.../passport-001.enc",
                "encryption_meta": {"scheme": "XChaCha20-Poly1305"},
                "created_at": "2024-01-15T10:30:00Z",
                "updated_at": "2024-01-15T10:30:00Z",
                "attestation_count": 1
            }
        }
    )


class DocumentUpdate(BaseModel):
    """Schema for updating document metadata"""
    display_name_encrypted: Optional[str] = Field(
        None,
        description="Updated encrypted display name"
    )
    file_meta: Optional[dict] = Field(
        None,
        description="Updated file metadata"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Updated expiration date"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "expires_at": "2035-01-15T00:00:00Z"
            }
        }
    )


class DocumentList(BaseModel):
    """Schema for listing documents"""
    documents: list[DocumentResponse]
    total: int = Field(..., description="Total number of documents")

