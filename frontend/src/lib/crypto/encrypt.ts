/**
 * ANCHOR Encryption Service
 * Client-side encryption utilities matching backend implementation
 * Uses XSalsa20-Poly1305 (via tweetnacl) for symmetric encryption
 */

import nacl from 'tweetnacl';
import { encodeBase64, decodeBase64, encodeUTF8, decodeUTF8 } from 'tweetnacl-util';

// Scheme identifiers matching backend
export const SCHEME_SECRETBOX = 'XSalsa20-Poly1305';
export const SCHEME_BOX = 'X25519-XSalsa20-Poly1305';

export interface EncryptedPayload {
  ciphertext: string; // base64
  nonce: string; // base64
  scheme: string;
  keyWrap?: {
    algorithm: string;
    ephemeral?: boolean;
    senderPubkey?: string;
  };
}

export interface VaultEncryptionMeta {
  scheme: string;
  nonce: string;
  key_wrap: {
    algorithm: string;
    wrapped_key: string;
    wrap_nonce: string;
  };
}

/**
 * Generate a random 32-byte symmetric encryption key
 */
export function generateKey(): Uint8Array {
  return nacl.randomBytes(nacl.secretbox.keyLength);
}

/**
 * Generate a random 24-byte nonce
 */
export function generateNonce(): Uint8Array {
  return nacl.randomBytes(nacl.secretbox.nonceLength);
}

/**
 * Encrypt data with a symmetric key using XSalsa20-Poly1305
 * Matches backend EncryptionService.encrypt_symmetric
 */
export function encryptSymmetric(
  plaintext: Uint8Array,
  key: Uint8Array,
  nonce?: Uint8Array
): EncryptedPayload {
  const nonceBytes = nonce || generateNonce();
  const ciphertext = nacl.secretbox(plaintext, nonceBytes, key);

  return {
    ciphertext: encodeBase64(ciphertext),
    nonce: encodeBase64(nonceBytes),
    scheme: SCHEME_SECRETBOX,
  };
}

/**
 * Decrypt data with a symmetric key
 * Matches backend EncryptionService.decrypt_symmetric
 */
/**
 * Custom error for decryption failures (e.g., incorrect password)
 * This allows callers to distinguish between expected and unexpected errors
 */
export class DecryptionError extends Error {
  constructor(message: string = 'Decryption failed: incorrect key or corrupted data') {
    super(message);
    this.name = 'DecryptionError';
  }
}

export function decryptSymmetric(
  payload: EncryptedPayload,
  key: Uint8Array
): Uint8Array {
  try {
    const ciphertext = decodeBase64(payload.ciphertext);
    const nonce = decodeBase64(payload.nonce);

    const decrypted = nacl.secretbox.open(ciphertext, nonce, key);
    if (!decrypted) {
      // Return null when decryption fails (typically wrong key/password)
      throw new DecryptionError('Decryption failed: incorrect key or corrupted data');
    }

    return decrypted;
  } catch (error) {
    // Re-throw DecryptionError as-is, but wrap other errors
    if (error instanceof DecryptionError) {
      throw error;
    }
    // Wrap unexpected errors
    throw new DecryptionError(`Decryption error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

/**
 * Encrypt data for a recipient using X25519 key exchange
 * Matches backend EncryptionService.encrypt_asymmetric
 */
export function encryptAsymmetric(
  plaintext: Uint8Array,
  recipientPublicKey: Uint8Array,
  senderSecretKey?: Uint8Array
): EncryptedPayload {
  // Generate ephemeral keypair if sender key not provided
  let senderKeyPair: nacl.BoxKeyPair;
  let ephemeral = false;

  if (senderSecretKey) {
    // Use provided keypair
    senderKeyPair = {
      publicKey: nacl.box.keyPair.fromSecretKey(senderSecretKey).publicKey,
      secretKey: senderSecretKey,
    };
  } else {
    // Generate ephemeral keypair
    senderKeyPair = nacl.box.keyPair();
    ephemeral = true;
  }

  const nonce = generateNonce();
  const ciphertext = nacl.box(
    plaintext,
    nonce,
    recipientPublicKey,
    senderKeyPair.secretKey
  );

  return {
    ciphertext: encodeBase64(ciphertext),
    nonce: encodeBase64(nonce),
    scheme: SCHEME_BOX,
    keyWrap: {
      algorithm: 'X25519-HKDF',
      ephemeral,
      senderPubkey: encodeBase64(senderKeyPair.publicKey),
    },
  };
}

/**
 * Decrypt data encrypted with X25519 key exchange
 * Matches backend EncryptionService.decrypt_asymmetric
 */
export function decryptAsymmetric(
  payload: EncryptedPayload,
  recipientSecretKey: Uint8Array,
  senderPublicKey?: Uint8Array
): Uint8Array {
  let senderPubKey: Uint8Array;

  if (senderPublicKey) {
    senderPubKey = senderPublicKey;
  } else if (payload.keyWrap?.senderPubkey) {
    senderPubKey = decodeBase64(payload.keyWrap.senderPubkey);
  } else {
    throw new Error('Sender public key required for decryption');
  }

  const ciphertext = decodeBase64(payload.ciphertext);
  const nonce = decodeBase64(payload.nonce);

  const decrypted = nacl.box.open(
    ciphertext,
    nonce,
    senderPubKey,
    recipientSecretKey
  );

  if (!decrypted) {
    throw new Error('Decryption failed');
  }

  return decrypted;
}

/**
 * Encrypt a document for vault storage
 * Uses envelope encryption matching backend EncryptionService.encrypt_for_vault
 *
 * 1. Generate a random data encryption key (DEK)
 * 2. Encrypt the document with the DEK
 * 3. Encrypt the DEK with the document key
 */
export function encryptForVault(
  plaintext: Uint8Array,
  documentKey: Uint8Array
): { encryptedBlob: Uint8Array; encryptionMeta: VaultEncryptionMeta } {
  // Generate data encryption key
  const dek = generateKey();

  // Encrypt document with DEK
  const documentNonce = generateNonce();
  const ciphertext = nacl.secretbox(plaintext, documentNonce, dek);

  // Wrap DEK with document key
  const dekNonce = generateNonce();
  const wrappedDek = nacl.secretbox(dek, dekNonce, documentKey);

  // Encryption metadata matching backend format
  const encryptionMeta: VaultEncryptionMeta = {
    scheme: SCHEME_SECRETBOX,
    nonce: encodeBase64(documentNonce),
    key_wrap: {
      algorithm: 'XSalsa20-Poly1305',
      wrapped_key: encodeBase64(wrappedDek),
      wrap_nonce: encodeBase64(dekNonce),
    },
  };

  return {
    encryptedBlob: ciphertext,
    encryptionMeta,
  };
}

/**
 * Decrypt a document from vault storage
 * Matches backend EncryptionService.decrypt_from_vault
 */
export function decryptFromVault(
  encryptedBlob: Uint8Array,
  encryptionMeta: VaultEncryptionMeta,
  documentKey: Uint8Array
): Uint8Array {
  // Unwrap DEK
  const wrappedDek = decodeBase64(encryptionMeta.key_wrap.wrapped_key);
  const wrapNonce = decodeBase64(encryptionMeta.key_wrap.wrap_nonce);

  const dek = nacl.secretbox.open(wrappedDek, wrapNonce, documentKey);
  if (!dek) {
    throw new Error('Failed to unwrap document encryption key');
  }

  // Decrypt document
  const documentNonce = decodeBase64(encryptionMeta.nonce);
  const decrypted = nacl.secretbox.open(encryptedBlob, documentNonce, dek);

  if (!decrypted) {
    throw new Error('Failed to decrypt document');
  }

  return decrypted;
}

/**
 * Generate SHA-256 hash of content for integrity verification
 */
export async function generateContentHash(content: Uint8Array): Promise<string> {
  // Create a new ArrayBuffer to ensure type compatibility
  const buffer = new ArrayBuffer(content.length);
  new Uint8Array(buffer).set(content);
  const hashBuffer = await crypto.subtle.digest('SHA-256', buffer);
  const hashArray = new Uint8Array(hashBuffer);
  return Array.from(hashArray)
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
}

/**
 * Encrypt a string for vault storage (convenience function)
 */
export function encryptStringForVault(
  plaintext: string,
  documentKey: Uint8Array
): { encryptedBlob: Uint8Array; encryptionMeta: VaultEncryptionMeta } {
  return encryptForVault(decodeUTF8(plaintext), documentKey);
}

/**
 * Decrypt a vault document to string (convenience function)
 */
export function decryptVaultToString(
  encryptedBlob: Uint8Array,
  encryptionMeta: VaultEncryptionMeta,
  documentKey: Uint8Array
): string {
  const decrypted = decryptFromVault(encryptedBlob, encryptionMeta, documentKey);
  return encodeUTF8(decrypted);
}
