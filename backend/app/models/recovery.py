"""
ANCHOR Recovery Role Model
The Recovery Graph - Defines relationships for death, succession, and recovery handling
"""

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.citizen import Citizen


class RoleType(str, Enum):
    """
    Recovery role types in the succession graph.
    
    - PRIMARY_OWNER: The account holder themselves
    - BENEFICIARY: Inherits access upon verified death (must be an account, not email)
    - VERIFIER: Independent party that must attest (notary, insurer, lawyer)
    - GUARDIAN: Can halt succession process, emergency contact
    """
    PRIMARY_OWNER = "primary_owner"
    BENEFICIARY = "beneficiary"
    VERIFIER = "verifier"
    GUARDIAN = "guardian"


class RecoveryStatus(str, Enum):
    """
    Status of a recovery role assignment.
    """
    PENDING = "pending"  # Invitation sent, not yet acknowledged
    ACTIVE = "active"  # Role confirmed by both parties
    SUSPENDED = "suspended"  # Temporarily suspended
    REVOKED = "revoked"  # Permanently removed


class RecoveryRole(Base):
    """
    The Recovery Graph Edge
    
    Each account has a graph of roles, not just a beneficiary name.
    This implements the 4-Layer Trigger Logic for death/succession handling:
    
    Layer 1 (Inactivity): No login for X months → Watch Mode
    Layer 2 (Claim): Beneficiary submits claim + certified docs
    Layer 3 (Quorum): At least 2 independent verifiers must attest
    Layer 4 (Cooling Off): Fixed delay where owner/guardians can halt
    
    Key principle: Beneficiaries must be accounts, not emails.
    This ensures cryptographic handshake for relationship acknowledgment.
    """
    __tablename__ = "recovery_roles"
    
    # Primary key
    role_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Recovery role identifier"
    )
    
    # The citizen who owns this role assignment (the account holder)
    citizen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citizens.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Account holder who defined this role"
    )
    
    # The citizen assigned to this role (beneficiary, verifier, guardian)
    # Must be another account - not an email address
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citizens.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Account assigned to this role (must be an ANCHOR account)"
    )
    
    # Role type
    role_type: Mapped[RoleType] = mapped_column(
        SQLEnum(RoleType, name="role_type"),
        nullable=False,
        index=True,
        comment="Type of recovery role"
    )
    
    # Priority for ordering (e.g., primary vs secondary beneficiary)
    priority: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Priority order (0 = highest priority)"
    )
    
    # Role status
    status: Mapped[RecoveryStatus] = mapped_column(
        SQLEnum(RecoveryStatus, name="recovery_status"),
        default=RecoveryStatus.PENDING,
        nullable=False,
        index=True,
        comment="Current status of this role assignment"
    )
    
    # Cryptographic acknowledgment - both parties must sign
    # Structure: { "owner_signature": "...", "target_signature": "...", "acknowledged_at": "..." }
    handshake: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=dict,
        comment="Cryptographic acknowledgment signatures from both parties"
    )
    
    # Permissions granted upon succession
    # Structure: { "vault_access": ["passport", "nib"], "read_only": true, "phase": "A" }
    succession_permissions: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=dict,
        comment="Permissions to grant during staged access release"
    )
    
    # For verifiers: what they are authorized to verify
    verification_scope: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        default=dict,
        comment="Scope of verification authority for verifier roles"
    )
    
    # Optional notes/reason for this role
    notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes or reason for this role assignment"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When this role was created"
    )
    
    acknowledged_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When both parties acknowledged the relationship"
    )
    
    revoked_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When this role was revoked"
    )
    
    # Relationships
    citizen: Mapped["Citizen"] = relationship(
        "Citizen",
        foreign_keys=[citizen_id],
        back_populates="recovery_roles_as_owner"
    )
    
    target: Mapped["Citizen"] = relationship(
        "Citizen",
        foreign_keys=[target_id],
        back_populates="recovery_roles_as_target"
    )
    
    def acknowledge_by_target(self, signature: str) -> None:
        """Record target's acknowledgment of this role"""
        # Create new dict to trigger SQLAlchemy change detection for JSONB
        new_handshake = dict(self.handshake) if self.handshake else {}
        new_handshake["target_signature"] = signature
        new_handshake["target_acknowledged_at"] = datetime.now(timezone.utc).isoformat()
        self.handshake = new_handshake  # Reassign to trigger change detection
        
        # If both signatures present, mark as acknowledged
        if self.handshake.get("owner_signature") and self.handshake.get("target_signature"):
            self.status = RecoveryStatus.ACTIVE
            self.acknowledged_at = datetime.now(timezone.utc)
    
    def acknowledge_by_owner(self, signature: str) -> None:
        """Record owner's signature for this role"""
        # Create new dict to trigger SQLAlchemy change detection for JSONB
        new_handshake = dict(self.handshake) if self.handshake else {}
        new_handshake["owner_signature"] = signature
        new_handshake["owner_signed_at"] = datetime.now(timezone.utc).isoformat()
        self.handshake = new_handshake  # Reassign to trigger change detection
    
    def revoke(self) -> None:
        """Revoke this recovery role"""
        self.status = RecoveryStatus.REVOKED
        self.revoked_at = datetime.now(timezone.utc)
    
    def is_active(self) -> bool:
        """Check if this role is currently active"""
        return self.status == RecoveryStatus.ACTIVE
    
    def __repr__(self) -> str:
        return f"<RecoveryRole(id={self.role_id}, type={self.role_type}, citizen={self.citizen_id}, target={self.target_id})>"

