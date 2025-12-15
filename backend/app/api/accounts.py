"""
ANCHOR Accounts API
Endpoints for citizen account management
"""

from uuid import UUID
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.citizen import Citizen, AccountStatus
from app.schemas.citizen import (
    CitizenCreate,
    CitizenResponse,
    CitizenUpdate,
    CitizenHeartbeat,
)
from app.security.did import DIDGenerator


router = APIRouter()


@router.post(
    "",
    response_model=CitizenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create new citizen account",
    description="Create a new ANCHOR account with DID generation. UUID-based, not email-based.",
)
async def create_account(
    account_data: CitizenCreate,
    db: AsyncSession = Depends(get_db),
) -> Citizen:
    """
    Create a new citizen account.
    
    The account is the root of the ANCHOR identity:
    - UUID-based identity (sovereign, not email-dependent)
    - DID (Decentralized Identifier) generated from public key
    - Recovery graph initialized
    """
    # Generate DID from public key
    # In production, validate the public key format
    import base64
    try:
        pubkey_bytes = base64.b64decode(account_data.owner_pubkey)
        if len(pubkey_bytes) != 32:
            raise ValueError("Public key must be 32 bytes")
        did = DIDGenerator.public_key_to_did(pubkey_bytes)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid public key format: {str(e)}"
        )
    
    # Check if DID already exists
    existing = await db.execute(
        select(Citizen).where(Citizen.did == did)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Account with this public key already exists"
        )
    
    # Create citizen account
    citizen = Citizen(
        did=did,
        owner_pubkey=account_data.owner_pubkey,
        status=AccountStatus.ACTIVE,
        recovery_graph=account_data.recovery_graph or {
            "beneficiaries": [],
            "verifiers": [],
            "guardians": [],
        },
        vault_index={},
    )
    
    db.add(citizen)
    await db.commit()
    await db.refresh(citizen)
    
    return citizen


@router.get(
    "/{account_id}",
    response_model=CitizenResponse,
    summary="Get citizen account",
    description="Retrieve account details by account ID",
)
async def get_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Citizen:
    """
    Get a citizen account by ID.
    
    In production, this endpoint would require authentication
    to ensure the requester has access to this account.
    """
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == account_id)
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return citizen


@router.get(
    "/did/{did}",
    response_model=CitizenResponse,
    summary="Get account by DID",
    description="Retrieve account details by Decentralized Identifier",
)
async def get_account_by_did(
    did: str,
    db: AsyncSession = Depends(get_db),
) -> Citizen:
    """
    Get a citizen account by DID.
    
    Useful for looking up accounts during attestation
    or recovery role setup.
    """
    result = await db.execute(
        select(Citizen).where(Citizen.did == did)
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return citizen


@router.patch(
    "/{account_id}",
    response_model=CitizenResponse,
    summary="Update citizen account",
    description="Update account settings (recovery graph, vault index)",
)
async def update_account(
    account_id: UUID,
    update_data: CitizenUpdate,
    db: AsyncSession = Depends(get_db),
) -> Citizen:
    """
    Update a citizen account.
    
    Only specific fields can be updated:
    - recovery_graph: Recovery relationships
    - vault_index: Document organization
    """
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == account_id)
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(citizen, field, value)
    
    # Update heartbeat on any activity
    citizen.update_heartbeat()
    
    await db.commit()
    await db.refresh(citizen)
    
    return citizen


@router.post(
    "/{account_id}/heartbeat",
    response_model=CitizenHeartbeat,
    summary="Update heartbeat",
    description="Record account activity to prevent inactivity-triggered watch mode",
)
async def update_heartbeat(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> Citizen:
    """
    Update the heartbeat timestamp.
    
    This is called on any authenticated activity to track
    account activity for Layer 1 of the recovery trigger logic
    (inactivity detection).
    """
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == account_id)
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    citizen.update_heartbeat()
    
    await db.commit()
    await db.refresh(citizen)
    
    return citizen


@router.get(
    "/{account_id}/status",
    summary="Get account status",
    description="Get current account status and recovery state",
)
async def get_account_status(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get detailed account status.
    
    Returns current status and relevant recovery information.
    """
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == account_id)
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Calculate days since last heartbeat
    now = datetime.now(timezone.utc)
    days_inactive = (now - citizen.last_heartbeat).days
    
    return {
        "account_id": citizen.account_id,
        "status": citizen.status,
        "last_heartbeat": citizen.last_heartbeat,
        "days_inactive": days_inactive,
        "recovery_graph_summary": {
            "beneficiaries": len(citizen.recovery_graph.get("beneficiaries", [])),
            "verifiers": len(citizen.recovery_graph.get("verifiers", [])),
            "guardians": len(citizen.recovery_graph.get("guardians", [])),
        } if citizen.recovery_graph else None,
    }

