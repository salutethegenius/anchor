"""
ANCHOR Attestation Schemas
Pydantic models for Verifiable Credential API request/response validation
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict

from app.models.attestation import RevocationStatus, CredentialType


class ProofSchema(BaseModel):
    """Schema for cryptographic proof (W3C Verifiable Credentials format)"""
    type: str = Field(
        default="Ed25519Signature2018",
        description="Proof type"
    )
    created: datetime = Field(
        ...,
        description="When the proof was created"
    )
    proof_purpose: str = Field(
        default="assertionMethod",
        description="Purpose of the proof"
    )
    verification_method: str = Field(
        ...,
        description="DID URL of the verification key"
    )
    proof_value: str = Field(
        ...,
        description="Base64-encoded signature"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "Ed25519Signature2018",
                "created": "2024-01-15T10:30:00Z",
                "proof_purpose": "assertionMethod",
                "verification_method": "did:key:z6Mkf5rG...#z6Mkf5rG",
                "proof_value": "base64-encoded-signature"
            }
        }
    )


class AttestationCreate(BaseModel):
    """
    Schema for creating a new attestation (Verifiable Credential).
    
    The issuer signs the credential with their Ed25519 key.
    The proof contains the cryptographic signature.
    """
    issuer_did: str = Field(
        ...,
        description="DID of the attestor (bank, lawyer, notary)",
        min_length=10
    )
    issuer_meta: Optional[dict] = Field(
        None,
        description="Issuer metadata (name, organization)"
    )
    subject_id: UUID = Field(
        ...,
        description="Account UUID this credential is about"
    )
    document_id: Optional[UUID] = Field(
        None,
        description="Document being attested to (if applicable)"
    )
    credential_type: CredentialType = Field(
        ...,
        description="Type of verifiable credential"
    )
    claims: dict = Field(
        ...,
        description="Credential claims/assertions"
    )
    proof: dict = Field(
        ...,
        description="Cryptographic signature"
    )
    expires_at: Optional[datetime] = Field(
        None,
        description="Credential expiration date"
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "issuer_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
                "issuer_meta": {
                    "name": "Bay Street Notary Services",
                    "role": "notary"
                },
                "subject_id": "550e8400-e29b-41d4-a716-446655440000",
                "document_id": "660e8400-e29b-41d4-a716-446655440000",
                "credential_type": "document_attestation",
                "claims": {
                    "document_verified": True,
                    "verification_method": "in_person",
                    "notes": "Passport verified at Bay Street office"
                },
                "proof": {
                    "type": "Ed25519Signature2018",
                    "created": "2024-01-15T10:30:00Z",
                    "proof_purpose": "assertionMethod",
                    "verification_method": "did:key:z6MkhaXg...#z6MkhaXg",
                    "proof_value": "base64-signature"
                },
                "expires_at": "2025-01-15T10:30:00Z"
            }
        }
    )


class AttestationResponse(BaseModel):
    """
    Schema for attestation response.
    Returns the full Verifiable Credential details.
    """
    attestation_id: UUID = Field(..., description="Attestation identifier")
    issuer_did: str = Field(..., description="Issuer's DID")
    issuer_meta: Optional[dict] = Field(None, description="Issuer metadata")
    subject_id: UUID = Field(..., description="Subject account ID")
    document_id: Optional[UUID] = Field(None, description="Related document ID")
    credential_type: CredentialType = Field(..., description="Credential type")
    claims: dict = Field(..., description="Credential claims")
    proof: dict = Field(..., description="Cryptographic proof")
    revocation_status: RevocationStatus = Field(..., description="Revocation status")
    revocation_reason: Optional[str] = Field(None, description="Revocation reason")
    issued_at: datetime = Field(..., description="Issue timestamp")
    expires_at: Optional[datetime] = Field(None, description="Expiration date")
    revoked_at: Optional[datetime] = Field(None, description="Revocation timestamp")
    is_valid: bool = Field(..., description="Whether credential is currently valid")
    
    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "attestation_id": "770e8400-e29b-41d4-a716-446655440000",
                "issuer_did": "did:key:z6MkhaXgBZDvotDkL5257faiztiGiC2QtKLGpbnnEGta2doK",
                "subject_id": "550e8400-e29b-41d4-a716-446655440000",
                "credential_type": "document_attestation",
                "claims": {"document_verified": True},
                "revocation_status": "active",
                "issued_at": "2024-01-15T10:30:00Z",
                "is_valid": True
            }
        }
    )


class AttestationRevoke(BaseModel):
    """Schema for revoking an attestation"""
    reason: str = Field(
        ...,
        description="Reason for revocation",
        min_length=1
    )
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "reason": "Document superseded by updated version"
            }
        }
    )


class AttestationList(BaseModel):
    """Schema for listing attestations"""
    attestations: list[AttestationResponse]
    total: int = Field(..., description="Total number of attestations")

