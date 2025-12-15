/**
 * ANCHOR API Types
 * TypeScript types matching backend Pydantic schemas
 */

// Account status enum matching backend
export type AccountStatus = 'active' | 'watch' | 'suspended' | 'in_succession';

// Document types matching backend
export type DocumentType =
  | 'passport'
  | 'nib'
  | 'voter'
  | 'insurance'
  | 'will'
  | 'property'
  | 'contract'
  | 'medical'
  | 'education'
  | 'other';

// Citizen/Account schemas
export interface CitizenCreate {
  owner_pubkey: string;
  recovery_graph?: RecoveryGraph;
}

export interface CitizenResponse {
  account_id: string;
  did: string;
  status: AccountStatus;
  recovery_graph: RecoveryGraph | null;
  vault_index: Record<string, unknown> | null;
  created_at: string;
  last_heartbeat: string;
}

export interface CitizenUpdate {
  recovery_graph?: RecoveryGraph;
  vault_index?: Record<string, unknown>;
}

export interface CitizenHeartbeat {
  account_id: string;
  last_heartbeat: string;
  status: AccountStatus;
}

export interface AccountStatusResponse {
  account_id: string;
  status: AccountStatus;
  last_heartbeat: string;
  days_inactive: number;
  recovery_graph_summary: {
    beneficiaries: number;
    verifiers: number;
    guardians: number;
  } | null;
}

// Recovery graph structure
export interface RecoveryGraph {
  beneficiaries: string[];
  verifiers: string[];
  guardians: string[];
}

// Document schemas
export interface EncryptionMeta {
  scheme: string;
  nonce: string;
  key_wrap: {
    algorithm: string;
    wrapped_key: string;
    wrap_nonce: string;
  };
}

export interface DocumentCreate {
  doc_type: DocumentType;
  display_name_encrypted?: string;
  ciphertext_ref: string;
  encryption_meta: EncryptionMeta;
  content_hash?: string;
  file_meta?: Record<string, unknown>;
  expires_at?: string;
}

export interface DocumentResponse {
  doc_id: string;
  owner_id: string;
  doc_type: DocumentType;
  display_name_encrypted: string | null;
  ciphertext_ref: string;
  encryption_meta: EncryptionMeta;
  content_hash: string | null;
  file_meta: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
  expires_at: string | null;
  attestation_count: number;
}

export interface DocumentUpdate {
  display_name_encrypted?: string;
  file_meta?: Record<string, unknown>;
  expires_at?: string;
}

export interface DocumentList {
  documents: DocumentResponse[];
  total: number;
}

// Attestation schemas
export type RevocationStatus = 'active' | 'revoked' | 'expired' | 'suspended';

export interface AttestationCreate {
  issuer_did: string;
  document_id?: string;
  credential_type: string;
  proof: Record<string, unknown>;
  expires_at?: string;
}

export interface AttestationResponse {
  attestation_id: string;
  issuer_did: string;
  subject_id: string;
  document_id: string | null;
  credential_type: string;
  proof: Record<string, unknown>;
  revocation_status: RevocationStatus;
  issued_at: string;
  expires_at: string | null;
  is_valid: boolean;
}

// Recovery role schemas
export type RoleType = 'primary_owner' | 'beneficiary' | 'verifier' | 'guardian';
export type RecoveryStatus = 'pending' | 'active' | 'revoked' | 'suspended';

export interface RecoveryRoleCreate {
  target_id: string;
  role_type: RoleType;
  priority?: number;
  succession_permissions?: {
    vault_access?: string[];
    read_only?: boolean;
    phase?: string;
  };
  verification_scope?: Record<string, unknown>;
  notes?: string;
  owner_signature: string;
}

export interface RecoveryRoleResponse {
  role_id: string;
  citizen_id: string;
  target_id: string;
  role_type: RoleType;
  priority: number;
  status: RecoveryStatus;
  handshake?: Record<string, unknown>;
  succession_permissions?: Record<string, unknown>;
  verification_scope?: Record<string, unknown>;
  notes?: string;
  created_at: string;
  acknowledged_at?: string;
  revoked_at?: string;
  is_active: boolean;
}

// WebAuthn schemas
export interface WebAuthnRegistrationStart {
  account_id: string;
}

export interface WebAuthnRegistrationOptions {
  challenge: string;
  rp: { id: string; name: string };
  user: { id: string; name: string; displayName: string };
  pubKeyCredParams: Array<{ type: 'public-key'; alg: number }>;
}

export interface WebAuthnAuthStart {
  account_id: string;
}

export interface WebAuthnAuthOptions {
  challenge: string;
  allowCredentials: Array<{ type: 'public-key'; id: string }>;
  timeout: number;
}

// API Error response
export interface ApiError {
  detail: string;
}
