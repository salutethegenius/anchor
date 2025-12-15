"""
ANCHOR Citizen Schemas
Pydantic models for Citizen API request/response validation
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.citizen import AccountStatus


class CitizenBase(BaseModel):
    """Base schema with common citizen fields"""
    pass


class CitizenCreate(BaseModel):
    """
    Schema for creating a new citizen account.
    
    The account is UUID-based, not email-based.
    DID and public key are generated during creation.
    """
    owner_pubkey: str = Field(
        ...,
        description="Owner's Ed25519 public key (base64 encoded)",
        min_length=32
    )
    recovery_graph: Optional[dict] = Field(
        default=None,
        description="Initial recovery graph structure"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "owner_pubkey": "base64-encoded-ed25519-public-key",
                "recovery_graph": {
                    "beneficiaries": [],
                    "verifiers": [],
                    "guardians": []
                }
            }
        }
    )


class CitizenResponse(BaseModel):
    """
    Schema for citizen account response.
    Returns account details without sensitive data.
    """
    account_id: UUID = Field(..., description="Unique account identifier")
    did: str = Field(..., description="Decentralized Identifier")
    status: AccountStatus = Field(..., description="Current account status")
    recovery_graph: Optional[dict] = Field(None, description="Recovery relationships")
    vault_index: Optional[dict] = Field(None, description="Vault contents index")
    created_at: datetime = Field(..., description="Account creation time")
    last_heartbeat: datetime = Field(..., description="Last activity time")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "account_id": "550e8400-e29b-41d4-a716-446655440000",
                "did": "did:key:z6Mkf5rGMoatrSj1f4CyvuHBeXJELe9RPdzo2PKGNCKVtZxP",
                "status": "active",
                "recovery_graph": {
                    "beneficiaries": [],
                    "verifiers": [],
                    "guardians": []
                },
                "vault_index": {},
                "created_at": "2024-01-15T10:30:00Z",
                "last_heartbeat": "2024-01-15T10:30:00Z"
            }
        }
    )


class CitizenUpdate(BaseModel):
    """
    Schema for updating citizen account.
    Only specific fields can be updated.
    """
    recovery_graph: Optional[dict] = Field(
        None,
        description="Updated recovery graph"
    )
    vault_index: Optional[dict] = Field(
        None,
        description="Updated vault index"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "recovery_graph": {
                    "beneficiaries": ["550e8400-e29b-41d4-a716-446655440001"],
                    "verifiers": [],
                    "guardians": []
                }
            }
        }
    )


class CitizenHeartbeat(BaseModel):
    """Response schema for heartbeat updates"""
    account_id: UUID
    last_heartbeat: datetime
    status: AccountStatus
    
    model_config = ConfigDict(from_attributes=True)

