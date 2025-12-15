/**
 * ANCHOR Key Derivation Module
 * Uses Web Crypto API for browser-native key derivation
 */

import nacl from 'tweetnacl';
import { encodeBase64, decodeBase64 } from 'tweetnacl-util';

// Default key derivation parameters
const DEFAULT_ITERATIONS = 100000;
const DEFAULT_HASH_LEN = 32;
const DEFAULT_SALT_LEN = 16;

export interface KeyDerivationParams {
  iterations?: number;
  hashLen?: number;
  saltLen?: number;
}

/**
 * Generate a cryptographically secure random salt
 */
export function generateSalt(length: number = DEFAULT_SALT_LEN): Uint8Array {
  return nacl.randomBytes(length);
}

/**
 * Check if Web Crypto API is available
 */
function checkWebCryptoAvailable(): void {
  if (typeof crypto === 'undefined' || !crypto.subtle) {
    throw new Error(
      'Web Crypto API is not available. This requires:\n' +
      '1. A secure context (HTTPS or localhost)\n' +
      '2. A modern browser with Web Crypto API support\n' +
      '3. If on mobile, ensure you are using HTTPS or localhost'
    );
  }
}

/**
 * Derive a key from a secret using PBKDF2-SHA256 (Web Crypto API)
 * This is browser-native and well-supported
 */
export async function deriveKey(
  secret: string,
  salt: Uint8Array,
  params: KeyDerivationParams = {}
): Promise<Uint8Array> {
  // Check if Web Crypto API is available
  checkWebCryptoAvailable();

  const {
    iterations = DEFAULT_ITERATIONS,
    hashLen = DEFAULT_HASH_LEN,
  } = params;

  const encoder = new TextEncoder();
  const secretBytes = encoder.encode(secret);
  
  try {
    // Import the password as a key
    const passwordKey = await crypto.subtle.importKey(
      'raw',
      secretBytes,
      'PBKDF2',
      false,
      ['deriveBits']
    );
  
    // Create a new ArrayBuffer for salt to ensure type compatibility
    const saltBuffer = new ArrayBuffer(salt.length);
    new Uint8Array(saltBuffer).set(salt);
    
    // Derive bits using PBKDF2
    const derivedBits = await crypto.subtle.deriveBits(
      {
        name: 'PBKDF2',
        salt: saltBuffer,
        iterations: iterations,
        hash: 'SHA-256',
      },
      passwordKey,
      hashLen * 8 // bits
    );
    
    return new Uint8Array(derivedBits);
  } catch (error) {
    if (error instanceof Error) {
      // Provide more helpful error messages
      if (error.message.includes('importKey') || error.message.includes('deriveBits')) {
        throw new Error(
          `Web Crypto API error: ${error.message}. ` +
          'Please ensure you are using HTTPS or localhost.'
        );
      }
      throw error;
    }
    throw new Error('Unknown error during key derivation');
  }
}

/**
 * Derive a key with a newly generated salt
 * Returns both the derived key and the salt
 */
export async function deriveKeyWithNewSalt(
  secret: string,
  params: KeyDerivationParams = {}
): Promise<{ key: Uint8Array; salt: Uint8Array }> {
  const salt = generateSalt(params.saltLen || DEFAULT_SALT_LEN);
  const key = await deriveKey(secret, salt, params);
  return { key, salt };
}

/**
 * Derive an encryption key with context binding
 */
export async function deriveEncryptionKey(
  masterSecret: string,
  salt: Uint8Array,
  context: string = 'encryption'
): Promise<Uint8Array> {
  // Combine secret with context for domain separation
  const combined = masterSecret + context;
  return deriveKey(combined, salt, { hashLen: 32 });
}

/**
 * Generate an Ed25519/X25519 keypair
 * The signing key can be used for signatures and the box keypair for encryption
 */
export function generateKeyPair(): {
  publicKey: Uint8Array;
  secretKey: Uint8Array;
} {
  // Generate signing keypair (Ed25519)
  const signingKeyPair = nacl.sign.keyPair();
  
  return {
    publicKey: signingKeyPair.publicKey,
    secretKey: signingKeyPair.secretKey,
  };
}

/**
 * Generate an X25519 keypair for encryption
 */
export function generateBoxKeyPair(): {
  publicKey: Uint8Array;
  secretKey: Uint8Array;
} {
  return nacl.box.keyPair();
}

/**
 * Encode keypair as base64 strings for storage/transmission
 */
export function keypairToBase64(
  secretKey: Uint8Array,
  publicKey: Uint8Array
): { secretKeyB64: string; publicKeyB64: string } {
  return {
    secretKeyB64: encodeBase64(secretKey),
    publicKeyB64: encodeBase64(publicKey),
  };
}

/**
 * Decode keypair from base64 strings
 */
export function keypairFromBase64(
  secretKeyB64: string,
  publicKeyB64: string
): { secretKey: Uint8Array; publicKey: Uint8Array } {
  return {
    secretKey: decodeBase64(secretKeyB64),
    publicKey: decodeBase64(publicKeyB64),
  };
}

/**
 * Encode bytes to base64
 */
export { encodeBase64, decodeBase64 };
