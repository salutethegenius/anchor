# ANCHOR

**Sovereign Digital Account Layer for Bahamians**

ANCHOR is not a "wallet" — it is a persistent, recoverable financial and civic anchor built specifically for The Bahamas. It binds money, identity, rights, permissions, and recovery into one sovereign infrastructure.

## Screenshots

### Landing Page
![Landing Page](./docs/screenshots/landing-page.png)
The welcoming landing page introduces ANCHOR with clear value propositions for Bahamians.

### Account Creation
![Account Creation](./docs/screenshots/account-creation.png)
Creating a sovereign digital account with passphrase-based encryption. No email required.

### Dashboard
![Dashboard](./docs/screenshots/dashboard.png)
Main dashboard showing account status, DID, and quick statistics for documents, attestations, and recovery network.

### Document Vault
![Document Vault](./docs/screenshots/vault.png)
Zero-knowledge encrypted document storage. All documents are encrypted client-side before upload.

### Recovery Network
![Recovery Network](./docs/screenshots/recovery.png)
Manage your recovery network with beneficiaries, verifiers, and guardians for account succession.

### Attestations
![Attestations](./docs/screenshots/attestations.png)
View verifiable credentials issued by Bahamian banks, lawyers, and notaries for your documents.

### Settings
![Settings](./docs/screenshots/settings.png)
Account settings showing DID, public key, and passkey (WebAuthn) registration options.

## Use Case

### The Problem

Bahamians need a secure, persistent digital identity that:
- **Survives death and incapacity**: Documents and assets shouldn't be locked away forever if someone passes away
- **Works without email/passwords**: Many Bahamians don't have reliable email access or struggle with password management
- **Respects privacy**: Government and institutions shouldn't see your private documents
- **Supports succession**: When someone dies, their beneficiaries should be able to access important documents legally
- **Is recoverable**: Lost keys shouldn't mean losing everything

### The Solution

ANCHOR provides a **sovereign digital account** specifically designed for Bahamian citizens that:

1. **Zero-Knowledge Vault**: Store Bahamian identity documents (Passport, NIB Card, Voter ID, Insurance) with client-side encryption. The server never sees your actual documents.

2. **Passkey Authentication**: Use Face ID, Touch ID, or security keys instead of passwords. No email required.

3. **Recovery Network**: Designate trusted Bahamians (family, lawyers, notaries) as:
   - **Beneficiaries**: Who inherits access upon your death
   - **Verifiers**: Who must confirm succession claims
   - **Guardians**: Who can help with account recovery

4. **4-Layer Succession Process**:
   - **Layer 1**: Inactivity detection → Watch mode
   - **Layer 2**: Beneficiary submits claim with certified documents (death certificate)
   - **Layer 3**: Verifiers attest to the claim (legal verification)
   - **Layer 4**: Cooling-off period with staged access release

5. **Verifiable Credentials**: Collect attestations from Bahamian banks, lawyers, and notaries. Your proofs travel with you.

### Target Users

- **Primary**: Bahamian citizens who want secure, recoverable document storage
- **Pilot Vertical**: Digital ID documents (Passport, NIB, Voter Card) + Insurance certificates
- **Future**: Estate planning, property documents, wills, medical records

## Core Value Proposition

- **UUID-based Identity**: Accounts are sovereign, not email-dependent
- **Zero-Knowledge Storage**: Server sees metadata, not content
- **Recovery & Succession**: Death, inheritance, and fraud handling at the account level
- **Verifiable Credentials**: W3C-compliant attestations for document verification
- **Built for The Bahamas**: Designed with Bahamian context, documents, and legal processes in mind

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Layer                            │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   React Frontend │  │   Encryption SDK (Client-side)  │   │
│  │   (Next.js 14+)  │  │   (TweetNaCl, Web Crypto API)  │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       API Layer                              │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │  FastAPI Server  │  │   WebAuthn Middleware (FIDO2)   │   │
│  │   (Python 3.14)  │  │   (Passkey Authentication)      │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Storage Layer                            │
│  ┌─────────────────┐  ┌─────────────────────────────────┐   │
│  │   PostgreSQL     │  │   Encrypted Blob Storage (S3)   │   │
│  │   (Metadata)     │  │   (Document Content)            │   │
│  └─────────────────┘  └─────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+ (backend)
- PostgreSQL 14+ (database)
- Node.js 18+ (frontend)

### Backend Setup

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
# Create .env file with:
# DATABASE_URL=postgresql+asyncpg://user:password@localhost/anchor
# (See Environment Variables section for full list)

# Run database migrations
alembic upgrade head

# Start the server
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The frontend will be available at http://localhost:3000

### API Documentation

Once the backend is running, access the interactive API docs:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Data Model

### Citizen (Account Root)
- **UUID-based identity**: Sovereign account identifier
- **DID (Decentralized Identifier)**: W3C-compatible `did:key` format
- **Status**: `active`, `watch`, `suspended`, `in_succession`
- **Recovery Graph**: Network of beneficiaries, verifiers, and guardians
- **Public Key**: Ed25519 public key for signatures

### Document (Vault)
- **Encrypted blob reference**: Zero-knowledge document storage
- **Types**: `passport`, `nib`, `voter`, `insurance`, `will`, `property`, `contract`, `medical`, `education`, `other`
- **Encryption metadata**: Client-side decryption keys (server never sees content)
- **File metadata**: Original filename, size, type (encrypted display name optional)

### Attestation (Verifiable Credential)
- **Issuer DID**: Bahamian bank, lawyer, notary, or institution
- **Subject DID**: The citizen being attested
- **Credential Type**: What is being attested (e.g., "Identity Verified", "Account Holder")
- **Cryptographic Proof**: Ed25519 signature
- **Revocation Status**: `active`, `revoked`, `expired`, `suspended`
- **W3C VC Compatible**: Standards-based verifiable credentials

### Recovery Role
- **Types**: `beneficiary`, `verifier`, `guardian`
- **Cryptographic Handshake**: Both parties must sign (mutual acknowledgment)
- **Status**: `pending`, `active`, `revoked`
- **Staged Access Permissions**: Control what beneficiaries can access during succession
- **Priority**: Order of access release

## Security

### Encryption

- **Symmetric Encryption**: XSalsa20-Poly1305 (via NaCl SecretBox)
  - Used for: Document encryption, private key encryption
- **Asymmetric Encryption**: X25519 for key exchange, Ed25519 for signatures
  - Used for: Key exchange, DID verification, attestations
- **Key Derivation**: 
  - **Backend**: Argon2id (server-side operations)
  - **Frontend**: PBKDF2-SHA256 via Web Crypto API (browser-native)

### Zero-Knowledge Design

1. **Client-side encryption**: Documents encrypted before upload
2. **Metadata only**: Server stores encrypted blob references, not content
3. **Key management**: Private keys encrypted with passphrase-derived keys
4. **No password recovery**: Keys are recoverable via recovery network, not password reset

### 4-Layer Recovery Trigger Logic

1. **Inactivity Detection**: No heartbeat for extended period → Account enters `watch` mode
2. **Succession Claim**: Beneficiary submits claim with certified documents (death certificate, legal proof)
3. **Verification Quorum**: 2+ verifiers must attest to the claim
4. **Cooling-Off Period**: 60-day delay with staged access release; owner/guardians can halt process

## API Endpoints

### Accounts

- `POST /api/accounts` - Create citizen account (requires public key)
- `GET /api/accounts/{id}` - Get account by ID
- `GET /api/accounts/did/{did}` - Get account by DID
- `PATCH /api/accounts/{id}` - Update account settings
- `POST /api/accounts/{id}/heartbeat` - Update activity timestamp
- `GET /api/accounts/{id}/status` - Get account status and recovery graph summary

### Vault (Documents)

- `POST /api/vault/documents?owner_id={id}` - Store encrypted document metadata
- `GET /api/vault/documents/{doc_id}` - Get document metadata
- `GET /api/vault/accounts/{owner_id}/documents` - List documents for account
- `PATCH /api/vault/documents/{doc_id}` - Update document metadata
- `DELETE /api/vault/documents/{doc_id}` - Delete document
- `GET /api/vault/documents/{doc_id}/attestations` - Get attestations for document

### Recovery

- `POST /api/recovery/roles?citizen_id={id}` - Create recovery role (beneficiary/verifier/guardian)
- `GET /api/recovery/accounts/{id}/roles` - List recovery roles for account
- `POST /api/recovery/roles/{role_id}/acknowledge` - Complete handshake (target acknowledges)
- `DELETE /api/recovery/roles/{role_id}` - Revoke recovery role
- `GET /api/recovery/accounts/{id}/recovery-graph` - Get complete recovery graph
- `POST /api/recovery/succession/claim` - Submit succession claim
- `POST /api/recovery/succession/{id}/halt` - Halt succession process (owner/guardian)

### Attestations

- `POST /api/attestations?subject_id={id}` - Issue verifiable credential
- `GET /api/attestations/{id}` - Get attestation details
- `GET /api/attestations/{id}/verify` - Verify attestation validity
- `POST /api/attestations/{id}/revoke` - Revoke attestation

### Authentication (WebAuthn)

- `POST /api/auth/webauthn/register/start` - Start passkey registration
- `POST /api/auth/webauthn/register/complete` - Complete passkey registration
- `POST /api/auth/webauthn/auth/start` - Start passkey authentication
- `POST /api/auth/webauthn/auth/complete` - Complete passkey authentication
- `GET /api/auth/webauthn/credentials/{account_id}` - List registered passkeys
- `DELETE /api/auth/webauthn/credentials/{credential_id}` - Delete passkey

## Development Status

### ✅ Completed (Sprint 1 & 2)

- [x] Backend API with FastAPI
- [x] Database models and migrations
- [x] Client-side encryption SDK
- [x] DID generation and management
- [x] Account creation and management
- [x] Document vault (metadata storage)
- [x] Recovery graph implementation
- [x] WebAuthn/FIDO2 passkey authentication
- [x] Frontend React application (Next.js 14)
- [x] Account creation flow
- [x] Login with passphrase
- [x] Dashboard and vault UI
- [x] Recovery network management UI
- [x] Attestations UI
- [x] Settings and passkey registration

### 🚧 In Progress / Known Limitations

- [ ] Document download functionality (metadata stored, blob storage pending)
- [ ] Actual S3/blob storage integration (currently metadata-only)
- [ ] Recovery role acknowledgment flow (requires cryptographic signatures)
- [ ] Succession claim workflow (backend ready, frontend UI pending)
- [ ] Change passphrase functionality
- [ ] Export recovery kit

### 📋 Planned (Future Sprints)

- [ ] Production deployment guide
- [ ] Mobile app (React Native)
- [ ] Notary/Attestor portal
- [ ] Bank integration APIs
- [ ] Digital passport/NIB display
- [ ] QR code verification for credentials
- [ ] Multi-language support (Bahamas context)

## Environment Variables

### Backend (.env)

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | - | ✅ Yes |
| `SECRET_KEY` | JWT/encryption secret | - | ✅ Yes (production) |
| `ARGON2_TIME_COST` | Argon2id iterations | 3 | No |
| `ARGON2_MEMORY_COST` | Argon2id memory (KB) | 65536 | No |
| `ARGON2_PARALLELISM` | Argon2id parallelism | 4 | No |
| `WEBAUTHN_RP_ID` | WebAuthn relying party ID | localhost | No |
| `WEBAUTHN_ORIGIN` | WebAuthn origin | http://localhost:3000 | No |

### Frontend (.env.local)

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `NEXT_PUBLIC_API_URL` | Backend API URL | http://localhost:8000 | No |

## Contributing

This is a sovereign infrastructure project for The Bahamas. 

**Key Principles:**
- Zero-knowledge architecture (client-side encryption)
- Sovereign identity (no email dependency)
- Recovery-first design (survives death/incapacity)
- Built for Bahamian context and legal processes

Contact the team for contribution guidelines.

## License

Proprietary - All rights reserved.

---

**Built with ❤️ for The Bahamas**
