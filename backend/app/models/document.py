"""
ANCHOR Document Model
The Vault Object - Encrypted document storage with zero-knowledge design
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.citizen import Citizen
    from app.models.attestation import Attestation


class DocumentType(str, Enum):
    """
    Supported document types for the pilot vertical.
    Digital ID plus Insurance focus.
    """
    PASSPORT = "passport"
    NIB = "nib"  # National Insurance Board
    VOTER = "voter"  # Voter registration card
    INSURANCE = "insurance"  # Vehicle/property insurance
    WILL = "will"  # Last will and testament
    BIRTH_CERTIFICATE = "birth_certificate"
    DRIVERS_LICENSE = "drivers_license"
    OTHER = "other"


class Document(Base):
    """
    The Document Object (The "Vault")
    
    Zero-knowledge design: Server stores metadata only, content is an
    encrypted blob reference. The server sees blobs, not identities.
    
    Key principles:
    - Never store raw documents unencrypted
    - Client-side encryption before upload
    - Ciphertext reference points to encrypted blob (S3)
    - Attestations are the valuable asset, not the raw document
    """
    __tablename__ = "documents"
    
    # Primary key
    doc_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Document identifier"
    )
    
    # Owner relationship
    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citizens.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Account that owns this document"
    )
    
    # Document type for classification
    doc_type: Mapped[DocumentType] = mapped_column(
        SQLEnum(DocumentType, name="document_type"),
        nullable=False,
        index=True,
        comment="Type of document stored"
    )
    
    # Display name (encrypted client-side, stored as ciphertext)
    display_name_encrypted: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Encrypted display name (client-side encryption)"
    )
    
    # Reference to encrypted blob storage (e.g., S3 key)
    # This is NOT the document content - just a pointer
    ciphertext_ref: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Reference/pointer to encrypted blob in storage (e.g., S3 key)"
    )
    
    # Encryption metadata for decryption
    # Structure: { "scheme": "XChaCha20-Poly1305", "key_wrap": {...}, "nonce": "..." }
    encryption_meta: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Encryption scheme and key wrap information"
    )
    
    # Content hash for integrity verification (of encrypted blob)
    content_hash: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="SHA-256 hash of encrypted content for integrity"
    )
    
    # File metadata (encrypted references, no raw data)
    file_meta: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=dict,
        comment="Encrypted file metadata (size, type, etc.)"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Document upload timestamp"
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Last modification timestamp"
    )
    
    # Expiry tracking for documents that expire (passports, insurance)
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Document expiration date if applicable"
    )
    
    # Soft delete support
    is_deleted: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Soft delete flag"
    )
    
    # Relationships
    owner: Mapped["Citizen"] = relationship(
        "Citizen",
        back_populates="documents"
    )
    
    attestations: Mapped[list["Attestation"]] = relationship(
        "Attestation",
        back_populates="document",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Document(doc_id={self.doc_id}, type={self.doc_type}, owner={self.owner_id})>"

