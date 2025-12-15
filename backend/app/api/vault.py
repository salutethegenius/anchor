"""
ANCHOR Vault API
Endpoints for encrypted document storage (zero-knowledge vault)
"""

from uuid import UUID
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.citizen import Citizen
from app.models.document import Document, DocumentType
from app.models.attestation import Attestation
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
    DocumentList,
)


router = APIRouter()


def document_to_response(document: Document, include_attestation_count: bool = True) -> dict:
    """Convert Document model to response dict with attestation count"""
    response = {
        "doc_id": document.doc_id,
        "owner_id": document.owner_id,
        "doc_type": document.doc_type,
        "display_name_encrypted": document.display_name_encrypted,
        "ciphertext_ref": document.ciphertext_ref,
        "encryption_meta": document.encryption_meta,
        "content_hash": document.content_hash,
        "file_meta": document.file_meta,
        "created_at": document.created_at,
        "updated_at": document.updated_at,
        "expires_at": document.expires_at,
        "attestation_count": 0,
    }
    
    # Only count attestations if they've been loaded
    if include_attestation_count and hasattr(document, 'attestations') and document.attestations is not None:
        response["attestation_count"] = len(document.attestations)
    
    return response


@router.post(
    "/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store encrypted document reference",
    description="Store a reference to an encrypted document blob. Zero-knowledge: server sees metadata only.",
)
async def create_document(
    owner_id: UUID,
    document_data: DocumentCreate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Store an encrypted document reference in the vault.
    
    The actual document content is:
    1. Encrypted client-side before upload
    2. Stored in blob storage (S3)
    3. Only the reference and metadata are stored here
    
    This implements zero-knowledge storage where the server
    never sees the raw document content.
    """
    # Verify owner exists
    result = await db.execute(
        select(Citizen).where(Citizen.account_id == owner_id)
    )
    citizen = result.scalar_one_or_none()
    
    if not citizen:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Owner account not found"
        )
    
    # Create document record
    document = Document(
        owner_id=owner_id,
        doc_type=document_data.doc_type,
        display_name_encrypted=document_data.display_name_encrypted,
        ciphertext_ref=document_data.ciphertext_ref,
        encryption_meta=document_data.encryption_meta,
        content_hash=document_data.content_hash,
        file_meta=document_data.file_meta or {},
        expires_at=document_data.expires_at,
    )
    
    db.add(document)
    
    # Update citizen heartbeat
    citizen.update_heartbeat()
    
    await db.commit()
    await db.refresh(document)
    
    # Return without attestation count for newly created documents
    return document_to_response(document, include_attestation_count=False)


@router.get(
    "/documents/{doc_id}",
    response_model=DocumentResponse,
    summary="Get document metadata",
    description="Retrieve document metadata and encryption info (not content)",
)
async def get_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get document metadata by ID.
    
    Returns metadata and encryption info needed to:
    1. Locate the encrypted blob in storage
    2. Decrypt the content client-side
    
    Does NOT return the actual document content.
    """
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.attestations))
        .where(Document.doc_id == doc_id)
        .where(Document.is_deleted == False)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return document_to_response(document)


@router.get(
    "/accounts/{owner_id}/documents",
    response_model=DocumentList,
    summary="List account documents",
    description="List all documents in an account's vault",
)
async def list_documents(
    owner_id: UUID,
    doc_type: Optional[DocumentType] = Query(None, description="Filter by document type"),
    skip: int = Query(0, ge=0, description="Skip records"),
    limit: int = Query(50, ge=1, le=100, description="Limit records"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    List all documents for an account.
    
    Supports filtering by document type and pagination.
    """
    # Build query
    query = (
        select(Document)
        .options(selectinload(Document.attestations))
        .where(Document.owner_id == owner_id)
        .where(Document.is_deleted == False)
    )
    
    if doc_type:
        query = query.where(Document.doc_type == doc_type)
    
    # Get total count
    count_query = (
        select(func.count())
        .select_from(Document)
        .where(Document.owner_id == owner_id)
        .where(Document.is_deleted == False)
    )
    if doc_type:
        count_query = count_query.where(Document.doc_type == doc_type)
    
    count_result = await db.execute(count_query)
    total = count_result.scalar()
    
    # Get documents
    query = query.offset(skip).limit(limit).order_by(Document.created_at.desc())
    result = await db.execute(query)
    documents = result.scalars().all()
    
    return {
        "documents": [document_to_response(doc) for doc in documents],
        "total": total,
    }


@router.patch(
    "/documents/{doc_id}",
    response_model=DocumentResponse,
    summary="Update document metadata",
    description="Update document metadata (not content)",
)
async def update_document(
    doc_id: UUID,
    update_data: DocumentUpdate,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Update document metadata.
    
    Can update:
    - display_name_encrypted: Encrypted display name
    - file_meta: File metadata
    - expires_at: Expiration date
    
    Cannot change encryption or ciphertext reference
    (would require re-uploading the document).
    """
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.attestations))
        .where(Document.doc_id == doc_id)
        .where(Document.is_deleted == False)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    # Update fields
    update_dict = update_data.model_dump(exclude_unset=True)
    for field, value in update_dict.items():
        setattr(document, field, value)
    
    await db.commit()
    await db.refresh(document)
    
    return document_to_response(document)


@router.delete(
    "/documents/{doc_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete document",
    description="Soft delete a document from the vault",
)
async def delete_document(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Soft delete a document.
    
    The document is marked as deleted but not removed from the database.
    The encrypted blob should also be deleted from storage (separate process).
    """
    result = await db.execute(
        select(Document)
        .where(Document.doc_id == doc_id)
        .where(Document.is_deleted == False)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    document.is_deleted = True
    await db.commit()


@router.get(
    "/documents/{doc_id}/attestations",
    summary="Get document attestations",
    description="List all verifiable credentials for a document",
)
async def get_document_attestations(
    doc_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get all attestations (verifiable credentials) for a document.
    
    These are the valuable assets - proofs that trusted parties
    have verified the document.
    """
    result = await db.execute(
        select(Document)
        .options(selectinload(Document.attestations))
        .where(Document.doc_id == doc_id)
        .where(Document.is_deleted == False)
    )
    document = result.scalar_one_or_none()
    
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found"
        )
    
    return {
        "doc_id": document.doc_id,
        "attestations": [
            {
                "attestation_id": att.attestation_id,
                "issuer_did": att.issuer_did,
                "credential_type": att.credential_type,
                "revocation_status": att.revocation_status,
                "issued_at": att.issued_at,
                "is_valid": att.is_valid(),
            }
            for att in document.attestations
        ],
        "total": len(document.attestations),
    }

