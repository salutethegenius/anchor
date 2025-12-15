"""
ANCHOR Pydantic Schemas
Request/Response models for API validation
"""

from app.schemas.citizen import (
    CitizenCreate,
    CitizenResponse,
    CitizenUpdate,
)
from app.schemas.document import (
    DocumentCreate,
    DocumentResponse,
    DocumentUpdate,
)
from app.schemas.attestation import (
    AttestationCreate,
    AttestationResponse,
)
from app.schemas.recovery import (
    RecoveryRoleCreate,
    RecoveryRoleResponse,
)

__all__ = [
    "CitizenCreate",
    "CitizenResponse",
    "CitizenUpdate",
    "DocumentCreate",
    "DocumentResponse",
    "DocumentUpdate",
    "AttestationCreate",
    "AttestationResponse",
    "RecoveryRoleCreate",
    "RecoveryRoleResponse",
]

