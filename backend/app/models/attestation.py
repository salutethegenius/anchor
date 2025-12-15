"""
ANCHOR Attestation Model
Verifiable Credentials - The real asset is the attestation, not the document
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
    from app.models.document import Document


class RevocationStatus(str, Enum):
    """
    Attestation revocation status.
    Verifiable Credentials can be revoked by the issuer.
    """
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"
    SUSPENDED = "suspended"


class CredentialType(str, Enum):
    """
    Types of verifiable credentials that can be issued.
    """
    IDENTITY_VERIFICATION = "identity_verification"
    DOCUMENT_ATTESTATION = "document_attestation"
    NOTARY_WITNESS = "notary_witness"
    INSURANCE_PROOF = "insurance_proof"
    BENEFICIARY_ACKNOWLEDGMENT = "beneficiary_acknowledgment"
    DEATH_VERIFICATION = "death_verification"
    SUCCESSION_APPROVAL = "succession_approval"


class Attestation(Base):
    """
    The Attestation (Verifiable Credential)
    
    The asset is the attestation, not the document itself. A bank officer,
    lawyer, or notary verifies a document and signs a Verifiable Credential (VC).
    
    This follows W3C Verifiable Credentials specification.
    The proof contains a cryptographic signature (Ed25519Signature2018).
    
    Key use cases:
    - Bank officer verifies passport identity
    - Lawyer witnesses will signing
    - Insurer attests to valid coverage
    - Beneficiary acknowledges relationship (for recovery handshake)
    """
    __tablename__ = "attestations"
    
    # Primary key
    attestation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Attestation identifier"
    )
    
    # Issuer DID - who signed this credential (bank, lawyer, notary)
    issuer_did: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="DID of the attestor (bank, lawyer, notary, insurer)"
    )
    
    # Issuer metadata (name, organization, etc.)
    issuer_meta: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=dict,
        comment="Issuer metadata (name, organization, role)"
    )
    
    # Subject - the citizen account this credential is about
    subject_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citizens.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Account UUID this credential is about"
    )
    
    # Optional document link - if attesting to a specific document
    document_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.doc_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Document being attested to (if applicable)"
    )
    
    # Credential type
    credential_type: Mapped[CredentialType] = mapped_column(
        SQLEnum(CredentialType, name="credential_type"),
        nullable=False,
        index=True,
        comment="Type of verifiable credential"
    )
    
    # The credential claims (what is being attested)
    # Structure varies by credential_type
    claims: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        default=dict,
        comment="Credential claims/assertions"
    )
    
    # Cryptographic proof (Ed25519Signature2018 format)
    # Structure: { "type": "Ed25519Signature2018", "created": "...", "proofValue": "..." }
    proof: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
        comment="Cryptographic signature proving issuer authenticity"
    )
    
    # Revocation status
    revocation_status: Mapped[RevocationStatus] = mapped_column(
        SQLEnum(RevocationStatus, name="revocation_status"),
        default=RevocationStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="Current revocation state of the credential"
    )
    
    # Revocation reason (if revoked)
    revocation_reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reason for revocation if applicable"
    )
    
    # Timestamps
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When the credential was issued"
    )
    
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        index=True,
        comment="Credential expiration date"
    )
    
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the credential was revoked"
    )
    
    # Relationships
    subject: Mapped["Citizen"] = relationship(
        "Citizen",
        back_populates="attestations_received"
    )
    
    document: Mapped[Optional["Document"]] = relationship(
        "Document",
        back_populates="attestations"
    )
    
    def revoke(self, reason: str) -> None:
        """Revoke this attestation with a reason"""
        self.revocation_status = RevocationStatus.REVOKED
        self.revocation_reason = reason
        self.revoked_at = datetime.now(timezone.utc)
    
    def is_valid(self) -> bool:
        """Check if attestation is currently valid"""
        if self.revocation_status != RevocationStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True
    
    def __repr__(self) -> str:
        return f"<Attestation(id={self.attestation_id}, type={self.credential_type}, issuer={self.issuer_did})>"

