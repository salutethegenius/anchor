"""
ANCHOR WebAuthn Credential Model
Storage for passkey credentials
"""

import uuid
from datetime import datetime, timezone
from typing import Optional, TYPE_CHECKING

from sqlalchemy import String, Text, DateTime, ForeignKey, Integer, LargeBinary
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.citizen import Citizen


class WebAuthnCredential(Base):
    """
    WebAuthn/Passkey Credential Storage
    
    Stores registered passkey credentials for passwordless authentication.
    Each citizen can have multiple credentials (e.g., Touch ID on phone,
    Face ID on laptop, hardware security key).
    """
    __tablename__ = "webauthn_credentials"
    
    # Primary key
    credential_db_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Internal database ID"
    )
    
    # Foreign key to citizen
    citizen_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("citizens.account_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Owner of this credential"
    )
    
    # Credential ID from WebAuthn (base64url encoded)
    credential_id: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        unique=True,
        index=True,
        comment="WebAuthn credential ID (base64url)"
    )
    
    # Credential public key (COSE format, base64 encoded)
    public_key: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Credential public key (COSE format, base64)"
    )
    
    # Sign counter for replay attack detection
    sign_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Signature counter for replay detection"
    )
    
    # Credential type/authenticator info
    transports: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Comma-separated list of transports (usb, nfc, ble, internal)"
    )
    
    # User-friendly name for the credential
    device_name: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="User-friendly name for this credential"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="When credential was registered"
    )
    
    last_used_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When credential was last used"
    )
    
    # Relationship to citizen
    citizen: Mapped["Citizen"] = relationship(
        "Citizen",
        back_populates="webauthn_credentials"
    )
    
    def update_sign_count(self, new_count: int) -> None:
        """Update sign count and last used timestamp"""
        self.sign_count = new_count
        self.last_used_at = datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return f"<WebAuthnCredential(citizen_id={self.citizen_id}, device={self.device_name})>"
