/**
 * ANCHOR Encryption SDK
 * Client-side cryptographic utilities for zero-knowledge vault
 */

// Key derivation
export {
  generateSalt,
  deriveKey,
  deriveKeyWithNewSalt,
  deriveEncryptionKey,
  generateKeyPair as generateBoxKeyPairFromKeys,
  generateBoxKeyPair,
  keypairToBase64,
  keypairFromBase64,
  encodeBase64,
  decodeBase64,
} from './keys';

// Encryption
export {
  SCHEME_SECRETBOX,
  SCHEME_BOX,
  generateKey,
  generateNonce,
  encryptSymmetric,
  decryptSymmetric,
  encryptAsymmetric,
  decryptAsymmetric,
  encryptForVault,
  decryptFromVault,
  generateContentHash,
  encryptStringForVault,
  decryptVaultToString,
  DecryptionError,
} from './encrypt';

export type { EncryptedPayload, VaultEncryptionMeta } from './encrypt';

// DID
export {
  generateKeyPair,
  publicKeyToDid,
  didToPublicKey,
  generateDid,
  createVerificationMethod,
  signMessage,
  verifySignature,
  signMessageBase64,
  verifySignatureBase64,
} from './did';
