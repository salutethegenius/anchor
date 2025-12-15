/**
 * ANCHOR API Client
 * Typed HTTP client for backend communication
 */

import type {
  CitizenCreate,
  CitizenResponse,
  CitizenUpdate,
  CitizenHeartbeat,
  AccountStatusResponse,
  DocumentCreate,
  DocumentResponse,
  DocumentUpdate,
  DocumentList,
  DocumentType,
  AttestationCreate,
  AttestationResponse,
  RecoveryRoleCreate,
  RecoveryRoleResponse,
  ApiError,
} from './types';

// API base URL - configurable via environment variable
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Custom error class for API errors
 */
export class ApiClientError extends Error {
  constructor(
    message: string,
    public status: number,
    public detail?: string
  ) {
    super(message);
    this.name = 'ApiClientError';
    // Ensure the detail property is accessible
    Object.defineProperty(this, 'detail', {
      value: detail,
      writable: false,
      enumerable: true,
    });
  }
}

/**
 * Base fetch wrapper with error handling
 */
async function request<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const config: RequestInit = {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
  };

  const response = await fetch(url, config);

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const error: ApiError = await response.json();
      detail = error.detail;
    } catch {
      detail = response.statusText;
    }
    throw new ApiClientError(
      `API request failed: ${response.status}`,
      response.status,
      detail
    );
  }

  // Handle 204 No Content
  if (response.status === 204) {
    return undefined as T;
  }

  return response.json();
}

/**
 * GET request
 */
function GET<T>(endpoint: string): Promise<T> {
  return request<T>(endpoint, { method: 'GET' });
}

/**
 * POST request
 */
function POST<T>(endpoint: string, body?: unknown): Promise<T> {
  return request<T>(endpoint, {
    method: 'POST',
    body: body ? JSON.stringify(body) : undefined,
  });
}

/**
 * PATCH request
 */
function PATCH<T>(endpoint: string, body: unknown): Promise<T> {
  return request<T>(endpoint, {
    method: 'PATCH',
    body: JSON.stringify(body),
  });
}

/**
 * DELETE request
 */
function DELETE<T>(endpoint: string): Promise<T> {
  return request<T>(endpoint, { method: 'DELETE' });
}

/**
 * ANCHOR API Client
 */
export const api = {
  /**
   * Account endpoints
   */
  accounts: {
    /**
     * Create a new citizen account
     */
    create: (data: CitizenCreate): Promise<CitizenResponse> =>
      POST<CitizenResponse>('/api/accounts', data),

    /**
     * Get account by ID
     */
    get: (accountId: string): Promise<CitizenResponse> =>
      GET<CitizenResponse>(`/api/accounts/${accountId}`),

    /**
     * Get account by DID
     */
    getByDid: (did: string): Promise<CitizenResponse> =>
      GET<CitizenResponse>(`/api/accounts/did/${encodeURIComponent(did)}`),

    /**
     * Update account settings
     */
    update: (accountId: string, data: CitizenUpdate): Promise<CitizenResponse> =>
      PATCH<CitizenResponse>(`/api/accounts/${accountId}`, data),

    /**
     * Update account heartbeat
     */
    heartbeat: (accountId: string): Promise<CitizenHeartbeat> =>
      POST<CitizenHeartbeat>(`/api/accounts/${accountId}/heartbeat`),

    /**
     * Get account status
     */
    status: (accountId: string): Promise<AccountStatusResponse> =>
      GET<AccountStatusResponse>(`/api/accounts/${accountId}/status`),
  },

  /**
   * Vault endpoints
   */
  vault: {
    /**
     * Create a new document
     */
    create: (ownerId: string, data: DocumentCreate): Promise<DocumentResponse> =>
      POST<DocumentResponse>(`/api/vault/documents?owner_id=${ownerId}`, data),

    /**
     * Get document by ID
     */
    get: (docId: string): Promise<DocumentResponse> =>
      GET<DocumentResponse>(`/api/vault/documents/${docId}`),

    /**
     * List documents for an account
     */
    list: (
      ownerId: string,
      options?: { docType?: DocumentType; skip?: number; limit?: number }
    ): Promise<DocumentList> => {
      const params = new URLSearchParams();
      if (options?.docType) params.set('doc_type', options.docType);
      if (options?.skip) params.set('skip', options.skip.toString());
      if (options?.limit) params.set('limit', options.limit.toString());
      const query = params.toString();
      return GET<DocumentList>(
        `/api/vault/accounts/${ownerId}/documents${query ? `?${query}` : ''}`
      );
    },

    /**
     * Update document metadata
     */
    update: (docId: string, data: DocumentUpdate): Promise<DocumentResponse> =>
      PATCH<DocumentResponse>(`/api/vault/documents/${docId}`, data),

    /**
     * Delete a document
     */
    delete: (docId: string): Promise<void> =>
      DELETE<void>(`/api/vault/documents/${docId}`),

    /**
     * Get document attestations
     */
    attestations: (
      docId: string
    ): Promise<{ doc_id: string; attestations: AttestationResponse[]; total: number }> =>
      GET(`/api/vault/documents/${docId}/attestations`),
  },

  /**
   * Attestation endpoints
   */
  attestations: {
    /**
     * Create a new attestation
     */
    create: (subjectId: string, data: AttestationCreate): Promise<AttestationResponse> =>
      POST<AttestationResponse>(`/api/attestations?subject_id=${subjectId}`, data),

    /**
     * Get attestation by ID
     */
    get: (attestationId: string): Promise<AttestationResponse> =>
      GET<AttestationResponse>(`/api/attestations/${attestationId}`),

    /**
     * Revoke an attestation
     */
    revoke: (attestationId: string): Promise<AttestationResponse> =>
      POST<AttestationResponse>(`/api/attestations/${attestationId}/revoke`),

    /**
     * Verify an attestation
     */
    verify: (
      attestationId: string
    ): Promise<{ attestation_id: string; is_valid: boolean; verification_timestamp: string }> =>
      GET(`/api/attestations/${attestationId}/verify`),
  },

  /**
   * Recovery endpoints
   */
  recovery: {
    /**
     * Create a recovery role
     */
    createRole: (citizenId: string, data: RecoveryRoleCreate): Promise<RecoveryRoleResponse> =>
      POST<RecoveryRoleResponse>(`/api/recovery/roles?citizen_id=${citizenId}`, data),

    /**
     * List recovery roles for an account
     */
    listRoles: (citizenId: string): Promise<{ roles: RecoveryRoleResponse[]; total: number }> =>
      GET<{ roles: RecoveryRoleResponse[]; total: number }>(`/api/recovery/accounts/${citizenId}/roles`),

    /**
     * Delete a recovery role
     */
    deleteRole: (roleId: string): Promise<void> =>
      DELETE<void>(`/api/recovery/roles/${roleId}`),

    /**
     * Get recovery graph for an account
     */
    getRecoveryGraph: (accountId: string): Promise<{
      account_id: string;
      recovery_graph: {
        beneficiaries: Array<{ role_id: string; target_id: string; priority: number }>;
        verifiers: Array<{ role_id: string; target_id: string; priority: number }>;
        guardians: Array<{ role_id: string; target_id: string; priority: number }>;
      };
      total_roles: number;
    }> =>
      GET(`/api/recovery/accounts/${accountId}/recovery-graph`),

    /**
     * Submit succession claim
     */
    submitSuccessionClaim: (data: {
      account_id: string;
      claimant_id: string;
      document_hashes: string[];
      claim_reason?: string;
    }): Promise<{ account_id: string; status: string; message: string }> =>
      POST('/api/recovery/succession/claim', data),
  },

  /**
   * Auth endpoints
   */
  auth: {
    /**
     * Start WebAuthn registration
     */
    startRegistration: (accountId: string) =>
      POST('/api/auth/webauthn/register/start', { account_id: accountId }),

    /**
     * Complete WebAuthn registration
     */
    completeRegistration: (data: {
      account_id: string;
      credential_id: string;
      public_key: string;
      attestation_object: string;
      client_data_json: string;
    }) => POST('/api/auth/webauthn/register/complete', data),

    /**
     * Start WebAuthn authentication
     */
    startAuthentication: (accountId: string) =>
      POST('/api/auth/webauthn/auth/start', { account_id: accountId }),

    /**
     * Complete WebAuthn authentication
     */
    completeAuthentication: (data: {
      account_id: string;
      credential_id: string;
      authenticator_data: string;
      signature: string;
      client_data_json: string;
    }) => POST('/api/auth/webauthn/auth/complete', data),
  },

  /**
   * Health check
   */
  health: (): Promise<{ status: string }> => GET('/health'),
};

export default api;
