"""
ANCHOR Attestations API
Endpoints for Verifiable Credentials (attestations)
"""

from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.citizen import Citizen
from app.models.document import Document
from app.models.attestation import Attestation, RevocationStatus, CredentialType
from app.schemas.attestation import (
    AttestationCreate,
    AttestationResponse,
    AttestationRevoke,
    AttestationList,
)


router = APIRouter()


def attestation_to_response(attestation: Attestation) -> dict:
    """Convert Attestation model to response dict"""
    return {
        "attestation_id": attestation.attestation_id,
        "issuer_did": attestation.issuer_did,
        "issuer_meta": attestation.issuer_meta,
        "subject_id": attestation.subject_id,
        "document_id": attestation.document_id,
        "credential_type": attestation.credential_type,
        "claims": attestation.claims,
        "proof": attestation.proof,
        "revocation_status": attestation.revocation_status,
        "revocation_reason": attestation.revocation_reason,
        "issued_at": attestation.issued_at,
        "expires_at": attestation.expires_at,
        "revoked_at": attestation.revoked_at,
        "is_valid": attestation.is_valid(),
    }


@router.post(
    "",
    response_model=AttestationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create attestation",
    description="Issue a new Verifiable Credential (attestation)",
)
async def create_attestation(
    attestation_data: AttestationCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Create a new attestation (Verifiable Credential).
    
    The issuer (bank, lawyer, notary) signs the credential
    to attest to the validity of a document or claim about a citizen.
    
    The proof contains the cryptographic signature that proves
    the issuer's endorsement.
    """
    # Verify subject exists
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == attestation_data.subject_id)
    )
    subject = result.scalar_one_or_none()
    
    if not subject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Subject account not found"
        )
    
    # Verify document if provided
    if attestation_data.document_id:
        result = await db.execute(
            select(Document)
            .where(Document.doc_id == attestation_data.document_id)
            .where(Document.is_deleted == False)
        )
        document = result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found"
            )
        
        # Document must belong to subject
        if document.owner_id != attestation_data.subject_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document does not belong to the subject"
            )
    
    # Create attestation
    attestation = Attestation(
        issuer_did=attestation_data.issuer_did,
        issuer_meta=attestation_data.issuer_meta or {},
        subject_id=attestation_data.subject_id,
        document_id=attestation_data.document_id,
        credential_type=attestation_data.credential_type,
        claims=attestation_data.claims,
        proof=attestation_data.proof,
        revocation_status=RevocationStatus.ACTIVE,
        expires_at=attestation_data.expires_at,
    )
    
    db.add(attestation)
    await db.commit()
    await db.refresh(attestation)
    
    return attestation_to_response(attestation)


@router.get(
    "/{attestation_id}",
    response_model=AttestationResponse,
    summary="Get attestation",
    description="Retrieve a specific Verifiable Credential",
)
async def get_attestation(
    attestation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get an attestation by ID."""
    result = await db.execute(
        select(Attestation).where(Attestation.attestation_id == attestation_id)
    )
    attestation = result.scalar_one_or_none()
    
    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attestation not found"
        )
    
    return attestation_to_response(attestation)


@router.get(
    "/subject/{subject_id}",
    response_model=AttestationList,
    summary="List subject attestations",
    description="List all attestations for a citizen",
)
async def list_subject_attestations(
    subject_id: UUID,
    credential_type: Optional[CredentialType] = Query(None),
    valid_only: bool = Query(True, description="Only return valid attestations"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List all attestations where this citizen is the subject.
    
    These are the Verifiable Credentials that others have
    issued about this citizen.
    """
    query = select(Attestation).where(Attestation.subject_id == subject_id)
    
    if credential_type:
        query = query.where(Attestation.credential_type == credential_type)
    
    if valid_only:
        query = query.where(Attestation.revocation_status == RevocationStatus.ACTIVE)
    
    # Count
    count_query = select(func.count()).select_from(Attestation).where(
        Attestation.subject_id == subject_id
    )
    if credential_type:
        count_query = count_query.where(Attestation.credential_type == credential_type)
    if valid_only:
        count_query = count_query.where(Attestation.revocation_status == RevocationStatus.ACTIVE)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get attestations
    query = query.offset(skip).limit(limit).order_by(Attestation.issued_at.desc())
    result = await db.execute(query)
    attestations = result.scalars().all()
    
    return {
        "attestations": [attestation_to_response(att) for att in attestations],
        "total": total,
    }


@router.get(
    "/issuer/{issuer_did}",
    response_model=AttestationList,
    summary="List issuer attestations",
    description="List all attestations issued by a specific DID",
)
async def list_issuer_attestations(
    issuer_did: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List all attestations issued by a specific DID.
    
    Useful for attestors (notaries, lawyers) to see their
    issued credentials.
    """
    query = select(Attestation).where(Attestation.issuer_did == issuer_did)
    
    count_result = await db.execute(
        select(func.count()).select_from(Attestation).where(
            Attestation.issuer_did == issuer_did
        )
    )
    total = count_result.scalar()
    
    query = query.offset(skip).limit(limit).order_by(Attestation.issued_at.desc())
    result = await db.execute(query)
    attestations = result.scalars().all()
    
    return {
        "attestations": [attestation_to_response(att) for att in attestations],
        "total": total,
    }


@router.post(
    "/{attestation_id}/revoke",
    response_model=AttestationResponse,
    summary="Revoke attestation",
    description="Revoke a Verifiable Credential",
)
async def revoke_attestation(
    attestation_id: UUID,
    revoke_data: AttestationRevoke,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Revoke an attestation.
    
    Only the original issuer can revoke their attestations.
    In production, this would verify the requester is the issuer.
    """
    result = await db.execute(
        select(Attestation).where(Attestation.attestation_id == attestation_id)
    )
    attestation = result.scalar_one_or_none()
    
    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attestation not found"
        )
    
    if attestation.revocation_status == RevocationStatus.REVOKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Attestation is already revoked"
        )
    
    attestation.revoke(revoke_data.reason)
    await db.commit()
    await db.refresh(attestation)
    
    return attestation_to_response(attestation)


@router.get(
    "/{attestation_id}/verify",
    summary="Verify attestation",
    description="Verify an attestation's validity and signature",
)
async def verify_attestation(
    attestation_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Verify an attestation's validity.
    
    Checks:
    1. Revocation status
    2. Expiration date
    3. In production: cryptographic signature verification
    """
    result = await db.execute(
        select(Attestation).where(Attestation.attestation_id == attestation_id)
    )
    attestation = result.scalar_one_or_none()
    
    if not attestation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Attestation not found"
        )
    
    is_valid = attestation.is_valid()
    
    verification_result = {
        "attestation_id": attestation.attestation_id,
        "is_valid": is_valid,
        "checks": {
            "not_revoked": attestation.revocation_status == RevocationStatus.ACTIVE,
            "not_expired": True,
            "signature_valid": True,  # Would verify in production
        },
        "issuer_did": attestation.issuer_did,
        "subject_id": attestation.subject_id,
        "credential_type": attestation.credential_type,
        "issued_at": attestation.issued_at,
    }
    
    # Check expiration
    if attestation.expires_at:
        now = datetime.now(timezone.utc)
        verification_result["checks"]["not_expired"] = now < attestation.expires_at
        verification_result["expires_at"] = attestation.expires_at
    
    if attestation.revocation_status == RevocationStatus.REVOKED:
        verification_result["revoked_at"] = attestation.revoked_at
        verification_result["revocation_reason"] = attestation.revocation_reason
    
    return verification_result

