"""
ANCHOR Citizen Model
The Account Root - Core identity for each Bahamian citizen in the system
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.document import Document
    from app.models.attestation import Attestation
    from app.models.recovery import RecoveryRole
    from app.models.credential import WebAuthnCredential


class AccountStatus(str, Enum):
    """
    Account status states for the recovery/succession flow.
    
    - ACTIVE: Normal operational state
    - WATCH: Triggered by inactivity (no heartbeat for X months)
    - SUSPENDED: Account frozen due to suspicious activity or fraud flag
    - IN_SUCCESSION: Death/incapacity claim in progress, staged access release active
    """
    ACTIVE = "active"
    WATCH = "watch"
    SUSPENDED = "suspended"
    IN_SUCCESSION = "in_succession"


class Citizen(Base):
    """
    The Citizen (Account Root)
    
    Core identity entity that binds money, identity, rights, permissions,
    and recovery into one infrastructure. UUID-based (not email-based)
    for sovereignty and privacy.
    
    The citizen is the anchor point for:
    - Documents (vault contents)
    - Attestations (verifiable credentials)
    - Recovery roles (beneficiaries, verifiers, guardians)
    """
    __tablename__ = "citizens"
    
    # Primary identity - UUID based, not email
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Primary account identifier (UUID, not email-based)"
    )
    
    # Decentralized Identifier for W3C interoperability
    did: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Decentralized Identifier (DID) for verifiable credentials"
    )
    
    # Public key for cryptographic operations (Ed25519)
    owner_pubkey: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Owner's Ed25519 public key (base64 encoded)"
    )
    
    # Account status for recovery/succession flow
    status: Mapped[AccountStatus] = mapped_column(
        SQLEnum(AccountStatus, name="account_status"),
        default=AccountStatus.ACTIVE,
        nullable=False,
        index=True,
        comment="Current account state in the recovery lifecycle"
    )
    
    # Recovery graph defines relationships for succession
    # Structure: { "beneficiaries": [...], "verifiers": [...], "guardians": [...] }
    recovery_graph: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=dict,
        comment="Graph of recovery roles and relationships"
    )
    
    # Vault index - encrypted reference to document structure
    # Server sees structure but not content
    vault_index: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=dict,
        comment="Index of vault contents (metadata only, encrypted refs)"
    )
    
    # Timestamps for audit and inactivity detection
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="Account creation timestamp"
    )
    
    # Heartbeat for inactivity monitoring (Layer 1 of recovery)
    last_heartbeat: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True,
        comment="Last activity timestamp for inactivity detection"
    )
    
    # WebAuthn credential ID for passkey authentication
    webauthn_credential_id: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="FIDO2/WebAuthn credential identifier"
    )
    
    # Relationships
    documents: Mapped[list["Document"]] = relationship(
        "Document",
        back_populates="owner",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    attestations_received: Mapped[list["Attestation"]] = relationship(
        "Attestation",
        back_populates="subject",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # Recovery roles where this citizen is the account holder
    recovery_roles_as_owner: Mapped[list["RecoveryRole"]] = relationship(
        "RecoveryRole",
        foreign_keys="RecoveryRole.citizen_id",
        back_populates="citizen",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    # Recovery roles where this citizen is assigned a role (beneficiary, etc.)
    recovery_roles_as_target: Mapped[list["RecoveryRole"]] = relationship(
        "RecoveryRole",
        foreign_keys="RecoveryRole.target_id",
        back_populates="target",
        lazy="selectin"
    )
    
    # WebAuthn credentials for passkey authentication
    webauthn_credentials: Mapped[list["WebAuthnCredential"]] = relationship(
        "WebAuthnCredential",
        back_populates="citizen",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
    
    def update_heartbeat(self) -> None:
        """Update the heartbeat timestamp to current time"""
        self.last_heartbeat = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return f"<Citizen(account_id={self.account_id}, did={self.did}, status={self.status})>"

