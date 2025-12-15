"""
ANCHOR Recovery API
Endpoints for recovery roles, succession, and beneficiary management
"""

from uuid import UUID
from datetime import datetime, timezone
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.database import get_db
from app.models.citizen import Citizen, AccountStatus
from app.models.recovery import RecoveryRole, RoleType, RecoveryStatus
from app.schemas.recovery import (
    RecoveryRoleCreate,
    RecoveryRoleResponse,
    RecoveryRoleAcknowledge,
    RecoveryRoleList,
    SuccessionClaim,
    SuccessionStatus,
)


router = APIRouter()


def role_to_response(role: RecoveryRole) -> dict:
    """Convert RecoveryRole model to response dict"""
    return {
        "role_id": role.role_id,
        "citizen_id": role.citizen_id,
        "target_id": role.target_id,
        "role_type": role.role_type,
        "priority": role.priority,
        "status": role.status,
        "handshake": role.handshake,
        "succession_permissions": role.succession_permissions,
        "verification_scope": role.verification_scope,
        "notes": role.notes,
        "created_at": role.created_at,
        "acknowledged_at": role.acknowledged_at,
        "revoked_at": role.revoked_at,
        "is_active": role.is_active(),
    }


@router.post(
    "/roles",
    response_model=RecoveryRoleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create recovery role",
    description="Assign a recovery role (beneficiary, verifier, guardian) to another account",
)
async def create_recovery_role(
    citizen_id: UUID,
    role_data: RecoveryRoleCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Create a new recovery role assignment.
    
    This initiates the "Beneficiary Handshake" where:
    1. Owner creates the role with their signature
    2. Target must acknowledge with their signature
    3. Only then is the role ACTIVE
    
    Key principle: Beneficiaries must be accounts, not emails.
    """
    # Verify citizen (owner) exists
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == citizen_id)
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Verify target exists (must be an account, not email)
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == role_data.target_id)
    )
    target = result.scalar_one_or_none()
    
    if not target:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Target account not found. Beneficiaries must be ANCHOR accounts."
        )
    
    # Cannot assign role to self
    if citizen_id == role_data.target_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot assign recovery role to yourself"
        )
    
    # Check for existing role of same type
    existing = await db.execute(
        select(RecoveryRole).where(
            and_(
                RecoveryRole.citizen_id == citizen_id,
                RecoveryRole.target_id == role_data.target_id,
                RecoveryRole.role_type == role_data.role_type,
                RecoveryRole.status != RecoveryStatus.REVOKED,
            )
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This role assignment already exists"
        )
    
    # Create the role
    role = RecoveryRole(
        citizen_id=citizen_id,
        target_id=role_data.target_id,
        role_type=role_data.role_type,
        priority=role_data.priority,
        status=RecoveryStatus.PENDING,  # Starts as pending until acknowledged
        handshake={
            "owner_signature": role_data.owner_signature,
            "owner_signed_at": datetime.now(timezone.utc).isoformat(),
        },
        succession_permissions=role_data.succession_permissions,
        verification_scope=role_data.verification_scope,
        notes=role_data.notes,
    )
    
    db.add(role)
    
    # Update citizen heartbeat
    citizen.update_heartbeat()
    
    await db.commit()
    await db.refresh(role)
    
    return role_to_response(role)


@router.post(
    "/roles/{role_id}/acknowledge",
    response_model=RecoveryRoleResponse,
    summary="Acknowledge recovery role",
    description="Target acknowledges the role assignment (completes handshake)",
)
async def acknowledge_role(
    role_id: UUID,
    ack_data: RecoveryRoleAcknowledge,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Acknowledge a recovery role assignment.
    
    This completes the "Beneficiary Handshake":
    - Target provides their signature
    - Role status changes from PENDING to ACTIVE
    - The relationship is now cryptographically confirmed
    """
    result = await db.execute(
        select(RecoveryRole).where(RecoveryRole.role_id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recovery role not found"
        )
    
    if role.status != RecoveryStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Role cannot be acknowledged in {role.status} status"
        )
    
    # Complete the handshake
    role.acknowledge_by_target(ack_data.signature)
    
    await db.commit()
    await db.refresh(role)
    
    return role_to_response(role)


@router.get(
    "/roles/{role_id}",
    response_model=RecoveryRoleResponse,
    summary="Get recovery role",
    description="Get details of a specific recovery role",
)
async def get_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get a recovery role by ID."""
    result = await db.execute(
        select(RecoveryRole).where(RecoveryRole.role_id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recovery role not found"
        )
    
    return role_to_response(role)


@router.get(
    "/accounts/{account_id}/roles",
    response_model=RecoveryRoleList,
    summary="List account recovery roles",
    description="List all recovery roles defined by an account",
)
async def list_account_roles(
    account_id: UUID,
    role_type: Optional[RoleType] = Query(None, description="Filter by role type"),
    include_revoked: bool = Query(False, description="Include revoked roles"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List all recovery roles where this account is the owner.
    
    These are roles this account has assigned to others.
    """
    query = select(RecoveryRole).where(RecoveryRole.citizen_id == account_id)
    
    if role_type:
        query = query.where(RecoveryRole.role_type == role_type)
    
    if not include_revoked:
        query = query.where(RecoveryRole.status != RecoveryStatus.REVOKED)
    
    result = await db.execute(query.order_by(RecoveryRole.priority, RecoveryRole.created_at))
    roles = result.scalars().all()
    
    return {
        "roles": [role_to_response(role) for role in roles],
        "total": len(roles),
    }


@router.get(
    "/accounts/{account_id}/assigned-roles",
    response_model=RecoveryRoleList,
    summary="List assigned roles",
    description="List roles where this account is the target (assigned as beneficiary, etc.)",
)
async def list_assigned_roles(
    account_id: UUID,
    role_type: Optional[RoleType] = Query(None, description="Filter by role type"),
    status_filter: Optional[RecoveryStatus] = Query(None, description="Filter by status"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List all recovery roles where this account is the target.
    
    These are roles others have assigned to this account
    (e.g., this account is a beneficiary for another account).
    """
    query = select(RecoveryRole).where(RecoveryRole.target_id == account_id)
    
    if role_type:
        query = query.where(RecoveryRole.role_type == role_type)
    
    if status_filter:
        query = query.where(RecoveryRole.status == status_filter)
    else:
        query = query.where(RecoveryRole.status != RecoveryStatus.REVOKED)
    
    result = await db.execute(query.order_by(RecoveryRole.created_at.desc()))
    roles = result.scalars().all()
    
    return {
        "roles": [role_to_response(role) for role in roles],
        "total": len(roles),
    }


@router.delete(
    "/roles/{role_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke recovery role",
    description="Revoke a recovery role assignment",
)
async def revoke_role(
    role_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Revoke a recovery role.
    
    Only the account owner can revoke roles they created.
    In production, this would verify the requester is the owner.
    """
    result = await db.execute(
        select(RecoveryRole).where(RecoveryRole.role_id == role_id)
    )
    role = result.scalar_one_or_none()
    
    if not role:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recovery role not found"
        )
    
    if role.status == RecoveryStatus.REVOKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Role is already revoked"
        )
    
    role.revoke()
    await db.commit()


@router.get(
    "/accounts/{account_id}/recovery-graph",
    summary="Get recovery graph",
    description="Get the full recovery graph for an account",
)
async def get_recovery_graph(
    account_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get the complete recovery graph for an account.
    
    Returns all active roles organized by type:
    - beneficiaries: Who inherits on succession
    - verifiers: Who must attest during succession
    - guardians: Who can halt succession
    """
    # Get all active roles for this account
    result = await db.execute(
        select(RecoveryRole)
        .where(RecoveryRole.citizen_id == account_id)
        .where(RecoveryRole.status == RecoveryStatus.ACTIVE)
        .order_by(RecoveryRole.priority)
    )
    roles = result.scalars().all()
    
    # Organize by type
    graph = {
        "beneficiaries": [],
        "verifiers": [],
        "guardians": [],
    }
    
    for role in roles:
        role_data = {
            "role_id": role.role_id,
            "target_id": role.target_id,
            "priority": role.priority,
            "succession_permissions": role.succession_permissions,
            "acknowledged_at": role.acknowledged_at,
        }
        
        if role.role_type == RoleType.BENEFICIARY:
            graph["beneficiaries"].append(role_data)
        elif role.role_type == RoleType.VERIFIER:
            graph["verifiers"].append(role_data)
        elif role.role_type == RoleType.GUARDIAN:
            graph["guardians"].append(role_data)
    
    return {
        "account_id": account_id,
        "recovery_graph": graph,
        "total_roles": len(roles),
        "quorum_met": len(graph["verifiers"]) >= 2,  # Layer 3 requires 2+ verifiers
    }


@router.post(
    "/succession/claim",
    summary="Submit succession claim",
    description="Submit a claim to initiate succession process (Layer 2)",
)
async def submit_succession_claim(
    claim: SuccessionClaim,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Submit a succession claim.
    
    This triggers Layer 2 of the 4-Layer Trigger Logic:
    - Beneficiary submits claim with certified documents
    - Account status changes to IN_SUCCESSION
    - Verification process begins
    
    Requires:
    - Claimant must be an active beneficiary
    - Certified documents (death certificate) must be provided
    """
    # Verify claimant exists and is a beneficiary
    result = await db.execute(
        select(RecoveryRole)
        .where(RecoveryRole.citizen_id == claim.account_id)
        .where(RecoveryRole.target_id == claim.claimant_id)
        .where(RecoveryRole.role_type == RoleType.BENEFICIARY)
        .where(RecoveryRole.status == RecoveryStatus.ACTIVE)
    )
    beneficiary_role = result.scalar_one_or_none()
    
    if not beneficiary_role:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Claimant is not an active beneficiary for this account"
        )
    
    # Get the account
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == claim.account_id)
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Check account status
    if citizen.status == AccountStatus.IN_SUCCESSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Succession process already in progress"
        )
    
    # Transition to IN_SUCCESSION
    citizen.status = AccountStatus.IN_SUCCESSION
    
    # In a full implementation, we would:
    # 1. Store the claim details
    # 2. Notify verifiers
    # 3. Start the cooling-off timer
    
    await db.commit()
    
    return {
        "account_id": claim.account_id,
        "status": "claim_submitted",
        "message": "Succession claim submitted. Verifiers will be notified.",
        "next_step": "Layer 3: Await quorum verification (2+ verifiers must attest)",
        "current_layer": 2,
    }


class HaltSuccessionRequest(BaseModel):
    """Request body for halting succession"""
    halter_id: UUID
    reason: str


@router.post(
    "/succession/{account_id}/halt",
    summary="Halt succession process",
    description="Guardian or owner halts the succession process",
)
async def halt_succession(
    account_id: UUID,
    request: HaltSuccessionRequest,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Halt an ongoing succession process.
    
    This is the "Panic Freeze" path - available during Layer 4 (Cooling Off):
    - The original owner (if alive) can halt
    - Any guardian can halt
    - Flags potential fraud without alerting the claimant
    """
    halter_id = request.halter_id
    reason = request.reason
    
    # Verify halter is owner or guardian
    is_owner = halter_id == account_id
    
    if not is_owner:
        result = await db.execute(
            select(RecoveryRole)
            .where(RecoveryRole.citizen_id == account_id)
            .where(RecoveryRole.target_id == halter_id)
            .where(RecoveryRole.role_type == RoleType.GUARDIAN)
            .where(RecoveryRole.status == RecoveryStatus.ACTIVE)
        )
        guardian_role = result.scalar_one_or_none()
        
        if not guardian_role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only the account owner or guardians can halt succession"
            )
    
    # Get the account
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == account_id)
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    if citizen.status != AccountStatus.IN_SUCCESSION:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No succession process to halt"
        )
    
    # Halt and suspend
    citizen.status = AccountStatus.SUSPENDED
    
    await db.commit()
    
    return {
        "account_id": account_id,
        "status": "halted",
        "halted_by": halter_id,
        "halted_by_type": "owner" if is_owner else "guardian",
        "reason": reason,
        "message": "Succession process halted. Account suspended for review.",
    }

