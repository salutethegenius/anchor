"""
ANCHOR Authentication API
WebAuthn/FIDO2 passkey authentication endpoints
"""

import base64
import os
import secrets
from uuid import UUID
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)
from webauthn.helpers import (
    bytes_to_base64url,
    base64url_to_bytes,
)
from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    ResidentKeyRequirement,
    AuthenticatorAttachment,
    PublicKeyCredentialDescriptor,
    RegistrationCredential,
    AuthenticationCredential,
)

from app.database import get_db
from app.models.citizen import Citizen
from app.models.credential import WebAuthnCredential
from app.config import get_settings

settings = get_settings()
router = APIRouter()

# In-memory challenge storage (use Redis in production)
# Key: account_id, Value: (challenge, expiration)
_challenges: Dict[str, tuple[bytes, datetime]] = {}

# WebAuthn configuration
RP_ID = "localhost"  # Change to actual domain in production
RP_NAME = "ANCHOR"
ORIGIN = "http://localhost:3000"  # Frontend origin


class WebAuthnRegistrationStart(BaseModel):
    """Request to start WebAuthn registration"""
    account_id: str


class WebAuthnRegistrationComplete(BaseModel):
    """Complete WebAuthn registration"""
    account_id: str
    credential_id: str
    public_key: str
    attestation_object: str
    client_data_json: str


class WebAuthnAuthStart(BaseModel):
    """Request to start WebAuthn authentication"""
    account_id: str


class WebAuthnAuthComplete(BaseModel):
    """Complete WebAuthn authentication"""
    account_id: str
    credential_id: str
    authenticator_data: str
    signature: str
    client_data_json: str


def _store_challenge(account_id: str, challenge: bytes) -> None:
    """Store challenge with 5-minute expiration"""
    expiration = datetime.now(timezone.utc) + timedelta(minutes=5)
    _challenges[account_id] = (challenge, expiration)


def _get_challenge(account_id: str) -> Optional[bytes]:
    """Get and consume challenge if not expired"""
    if account_id not in _challenges:
        return None
    
    challenge, expiration = _challenges[account_id]
    del _challenges[account_id]  # Consume challenge
    
    if datetime.now(timezone.utc) > expiration:
        return None
    
    return challenge


@router.post("/webauthn/register/start")
async def start_registration(
    request: WebAuthnRegistrationStart,
    db: AsyncSession = Depends(get_db),
):
    """
    Start WebAuthn passkey registration.
    
    Returns challenge and options for the client to create a new credential.
    """
    # Verify account exists
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == UUID(request.account_id))
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Get existing credentials to exclude
    existing_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred.credential_id))
        for cred in citizen.webauthn_credentials
    ]
    
    # Generate registration options
    options = generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=str(citizen.account_id).encode(),
        user_name=citizen.did,
        user_display_name=f"ANCHOR User",
        exclude_credentials=existing_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.PREFERRED,
            resident_key=ResidentKeyRequirement.PREFERRED,
        ),
        timeout=60000,
    )
    
    # Store challenge for verification
    _store_challenge(request.account_id, options.challenge)
    
    # Convert to JSON-serializable format
    return options_to_json(options)


@router.post("/webauthn/register/complete")
async def complete_registration(
    request: WebAuthnRegistrationComplete,
    db: AsyncSession = Depends(get_db),
):
    """
    Complete WebAuthn passkey registration.
    
    Verifies the attestation and stores the credential.
    """
    # Get stored challenge
    challenge = _get_challenge(request.account_id)
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge expired or not found. Please start registration again."
        )
    
    # Verify account exists
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == UUID(request.account_id))
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    try:
        # Build credential from request
        credential = RegistrationCredential(
            id=request.credential_id,
            raw_id=base64url_to_bytes(request.credential_id),
            response={
                "attestationObject": base64url_to_bytes(request.attestation_object),
                "clientDataJSON": base64url_to_bytes(request.client_data_json),
            },
            type="public-key",
            authenticator_attachment=None,
            client_extension_results={},
        )
        
        # Verify registration response
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
        )
        
        # Store credential in database
        webauthn_cred = WebAuthnCredential(
            citizen_id=citizen.account_id,
            credential_id=request.credential_id,
            public_key=bytes_to_base64url(verification.credential_public_key),
            sign_count=verification.sign_count,
            transports=None,  # Could extract from response
            device_name="Passkey",
        )
        
        db.add(webauthn_cred)
        await db.commit()
        
        return {
            "status": "success",
            "message": "Passkey registered successfully",
            "credential_id": request.credential_id,
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Registration verification failed: {str(e)}"
        )


@router.post("/webauthn/auth/start")
async def start_authentication(
    request: WebAuthnAuthStart,
    db: AsyncSession = Depends(get_db),
):
    """
    Start WebAuthn authentication.
    
    Returns challenge and allowed credentials for the client.
    """
    # Verify account exists and has credentials
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == UUID(request.account_id))
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    if not citizen.webauthn_credentials:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No passkeys registered for this account"
        )
    
    # Get allowed credentials
    allowed_credentials = [
        PublicKeyCredentialDescriptor(id=base64url_to_bytes(cred.credential_id))
        for cred in citizen.webauthn_credentials
    ]
    
    # Generate authentication options
    options = generate_authentication_options(
        rp_id=RP_ID,
        allow_credentials=allowed_credentials,
        user_verification=UserVerificationRequirement.PREFERRED,
        timeout=60000,
    )
    
    # Store challenge for verification
    _store_challenge(request.account_id, options.challenge)
    
    # Convert to JSON-serializable format
    return options_to_json(options)


@router.post("/webauthn/auth/complete")
async def complete_authentication(
    request: WebAuthnAuthComplete,
    db: AsyncSession = Depends(get_db),
):
    """
    Complete WebAuthn authentication.
    
    Verifies the assertion and returns a session token.
    """
    # Get stored challenge
    challenge = _get_challenge(request.account_id)
    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Challenge expired or not found. Please start authentication again."
        )
    
    # Find the credential
    result = await db.execute(
        select(WebAuthnCredential)
        .where(WebAuthnCredential.credential_id == request.credential_id)
    )
    stored_cred = result.scalar_one_or_none()
    
    if not stored_cred:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credential not found"
        )
    
    try:
        # Build credential from request
        credential = AuthenticationCredential(
            id=request.credential_id,
            raw_id=base64url_to_bytes(request.credential_id),
            response={
                "authenticatorData": base64url_to_bytes(request.authenticator_data),
                "clientDataJSON": base64url_to_bytes(request.client_data_json),
                "signature": base64url_to_bytes(request.signature),
            },
            type="public-key",
            authenticator_attachment=None,
            client_extension_results={},
        )
        
        # Verify authentication response
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=challenge,
            expected_origin=ORIGIN,
            expected_rp_id=RP_ID,
            credential_public_key=base64url_to_bytes(stored_cred.public_key),
            credential_current_sign_count=stored_cred.sign_count,
        )
        
        # Update sign count
        stored_cred.update_sign_count(verification.new_sign_count)
        
        # Update citizen heartbeat
        citizen_result = await db.execute(
            select(Citizen).where(Citizen.account_id == stored_cred.citizen_id)
        )
        citizen = citizen_result.scalar_one()
        citizen.update_heartbeat()
        
        await db.commit()
        
        # In production, generate and return a JWT session token
        return {
            "status": "success",
            "message": "Authentication successful",
            "account_id": str(stored_cred.citizen_id),
            # "token": generate_jwt(stored_cred.citizen_id),  # TODO: Implement JWT
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Authentication verification failed: {str(e)}"
        )


@router.get("/webauthn/credentials/{account_id}")
async def list_credentials(
    account_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    List registered passkeys for an account.
    """
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == UUID(account_id))
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    return {
        "credentials": [
            {
                "credential_id": cred.credential_id,
                "device_name": cred.device_name,
                "created_at": cred.created_at.isoformat(),
                "last_used_at": cred.last_used_at.isoformat() if cred.last_used_at else None,
            }
            for cred in citizen.webauthn_credentials
        ],
        "total": len(citizen.webauthn_credentials),
    }


@router.delete("/webauthn/credentials/{credential_id}")
async def delete_credential(
    credential_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Delete a passkey credential.
    """
    result = await db.execute(
        select(WebAuthnCredential)
        .where(WebAuthnCredential.credential_id == credential_id)
    )
    credential = result.scalar_one_or_none()
    
    if not credential:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Credential not found"
        )
    
    await db.delete(credential)
    await db.commit()
    
    return {"status": "success", "message": "Credential deleted"}
