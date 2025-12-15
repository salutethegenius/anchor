"""
ANCHOR Recovery Role Schemas
Pydantic models for Recovery/Succession API request/response validation
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.recovery import RoleType, RecoveryStatus


class HandshakeSchema(BaseModel):
    """Schema for the cryptographic handshake between parties"""
    owner_signature: Optional[str] = Field(
        None,
        description="Owner's Ed25519 signature"
    )
    owner_signed_at: Optional[datetime] = Field(
        None,
        description="When owner signed"
    )
    target_signature: Optional[str] = Field(
        None,
        description="Target's Ed25519 signature"
    )
    target_acknowledged_at: Optional[datetime] = Field(
        None,
        description="When target acknowledged"
    )


class SuccessionPermissions(BaseModel):
    """Schema for permissions granted upon succession"""
    vault_access: list[str] = Field(
        default=[],
        description="Document types accessible"
    )
    read_only: bool = Field(
        default=True,
        description="Whether access is read-only"
    )
    phase: str = Field(
        default="A",
        description="Succession phase (A=read-only, B=limited, C=full)"
    )


class RecoveryRoleCreate(BaseModel):
    """
    Schema for creating a new recovery role.
    
    Implements the Recovery Graph - beneficiaries must be accounts,
    not email addresses, to enable cryptographic handshake.
    """
    target_id: UUID = Field(
        ...,
        description="Account UUID of the person being assigned this role"
    )
    role_type: RoleType = Field(
        ...,
        description="Type of recovery role"
    )
    priority: int = Field(
        default=0,
        ge=0,
        description="Priority order (0 = highest)"
    )
    succession_permissions: Optional[dict] = Field(
        None,
        description="Permissions to grant during staged access release"
    )
    verification_scope: Optional[dict] = Field(
        None,
        description="Scope for verifier roles"
    )
    notes: Optional[str] = Field(
        None,
        description="Notes for this role assignment"
    )
    owner_signature: str = Field(
        ...,
        description="Owner's signature to initiate the role",
        min_length=32
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "target_id": "660e8400-e29b-41d4-a716-446655440000",
                "role_type": "beneficiary",
                "priority": 0,
                "succession_permissions": {
                    "vault_access": ["passport", "nib", "will"],
                    "read_only": True,
                    "phase": "A"
                },
                "notes": "Primary beneficiary - spouse",
                "owner_signature": "base64-ed25519-signature"
            }
        }
    )


class RecoveryRoleResponse(BaseModel):
    """
    Schema for recovery role response.
    Shows the full relationship details.
    """
    role_id: UUID = Field(..., description="Role identifier")
    citizen_id: UUID = Field(..., description="Account holder ID")
    target_id: UUID = Field(..., description="Assigned account ID")
    role_type: RoleType = Field(..., description="Type of role")
    priority: int = Field(..., description="Priority order")
    status: RecoveryStatus = Field(..., description="Role status")
    handshake: Optional[dict] = Field(None, description="Handshake signatures")
    succession_permissions: Optional[dict] = Field(
        None,
        description="Succession permissions"
    )
    verification_scope: Optional[dict] = Field(
        None,
        description="Verification scope"
    )
    notes: Optional[str] = Field(None, description="Notes")
    created_at: datetime = Field(..., description="Creation timestamp")
    acknowledged_at: Optional[datetime] = Field(
        None,
        description="When both parties acknowledged"
    )
    revoked_at: Optional[datetime] = Field(None, description="Revocation timestamp")
    is_active: bool = Field(..., description="Whether role is currently active")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "role_id": "880e8400-e29b-41d4-a716-446655440000",
                "citizen_id": "550e8400-e29b-41d4-a716-446655440000",
                "target_id": "660e8400-e29b-41d4-a716-446655440000",
                "role_type": "beneficiary",
                "priority": 0,
                "status": "active",
                "is_active": True,
                "created_at": "2024-01-15T10:30:00Z",
                "acknowledged_at": "2024-01-16T14:00:00Z"
            }
        }
    )


class RecoveryRoleAcknowledge(BaseModel):
    """Schema for acknowledging a recovery role (by the target)"""
    signature: str = Field(
        ...,
        description="Target's Ed25519 signature acknowledging the role",
        min_length=32
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "signature": "base64-ed25519-signature"
            }
        }
    )


class RecoveryRoleList(BaseModel):
    """Schema for listing recovery roles"""
    roles: list[RecoveryRoleResponse]
    total: int = Field(..., description="Total number of roles")


class SuccessionClaim(BaseModel):
    """
    Schema for initiating a succession claim (beneficiary claim).
    
    This triggers Layer 2 of the 4-Layer Trigger Logic.
    Requires certified documents (death certificate).
    """
    claimant_id: UUID = Field(
        ...,
        description="Account ID of the beneficiary making the claim"
    )
    account_id: UUID = Field(
        ...,
        description="Account ID of the deceased/incapacitated"
    )
    claim_type: str = Field(
        ...,
        description="Type of claim (death, incapacity)"
    )
    certified_docs_ref: str = Field(
        ...,
        description="Reference to certified documents (death cert, etc.)"
    )
    claimant_signature: str = Field(
        ...,
        description="Claimant's signature on the claim"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "claimant_id": "660e8400-e29b-41d4-a716-446655440000",
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "claim_type": "death",
                "certified_docs_ref": "vault/claims/death-cert-001.enc",
                "claimant_signature": "base64-signature"
            }
        }
    )


class SuccessionStatus(BaseModel):
    """Schema for succession process status"""
    account_id: UUID
    status: str = Field(..., description="Current succession status")
    layer: int = Field(..., description="Current layer in 4-layer process (1-4)")
    claims: list[dict] = Field(default=[], description="Submitted claims")
    verifications: list[dict] = Field(default=[], description="Verifier attestations")
    cooling_off_ends: Optional[datetime] = Field(
        None,
        description="When cooling off period ends"
    )
    can_proceed: bool = Field(..., description="Whether succession can proceed")

