/**
 * ANCHOR DID (Decentralized Identifier) Module
 * Generate and manage DIDs using the did:key method
 * Matches backend DIDGenerator implementation
 */

import nacl from 'tweetnacl';
import { encodeBase64, decodeBase64 } from 'tweetnacl-util';

// Multicodec prefixes for did:key
// Ed25519 public key prefix: 0xed01
const ED25519_MULTICODEC_PREFIX = new Uint8Array([0xed, 0x01]);

// Base58 Bitcoin alphabet
const BASE58_ALPHABET = '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz';

/**
 * Encode bytes to base58btc (Bitcoin alphabet)
 * This is the multibase encoding used by did:key with 'z' prefix
 */
function base58Encode(data: Uint8Array): string {
  // Convert Uint8Array to bigint
  let num = BigInt(0);
  for (const byte of data) {
    num = num * BigInt(256) + BigInt(byte);
  }

  if (num === BigInt(0)) {
    return BASE58_ALPHABET[0];
  }

  const result: string[] = [];
  while (num > BigInt(0)) {
    const remainder = Number(num % BigInt(58));
    result.push(BASE58_ALPHABET[remainder]);
    num = num / BigInt(58);
  }

  // Handle leading zeros
  for (const byte of data) {
    if (byte === 0) {
      result.push(BASE58_ALPHABET[0]);
    } else {
      break;
    }
  }

  return result.reverse().join('');
}

/**
 * Decode base58btc string to bytes
 */
function base58Decode(encoded: string): Uint8Array {
  if (!encoded) {
    return new Uint8Array(0);
  }

  let num = BigInt(0);
  for (const char of encoded) {
    const index = BASE58_ALPHABET.indexOf(char);
    if (index === -1) {
      throw new Error(`Invalid base58 character: ${char}`);
    }
    num = num * BigInt(58) + BigInt(index);
  }

  // Handle leading zeros (1s in base58)
  let leadingZeros = 0;
  for (const char of encoded) {
    if (char === BASE58_ALPHABET[0]) {
      leadingZeros++;
    } else {
      break;
    }
  }

  // Convert number to bytes
  if (num === BigInt(0)) {
    return new Uint8Array(leadingZeros);
  }

  // Determine byte length
  const hex = num.toString(16);
  const byteLength = Math.ceil(hex.length / 2);
  const bytes = new Uint8Array(leadingZeros + byteLength);

  for (let i = 0; i < byteLength; i++) {
    bytes[leadingZeros + byteLength - 1 - i] = Number(
      (num >> BigInt(i * 8)) & BigInt(0xff)
    );
  }

  return bytes;
}

/**
 * Generate a new Ed25519 keypair for signing and DID
 */
export function generateKeyPair(): {
  signingKey: Uint8Array;
  verifyKey: Uint8Array;
} {
  const keyPair = nacl.sign.keyPair();
  return {
    signingKey: keyPair.secretKey,
    verifyKey: keyPair.publicKey,
  };
}

/**
 * Convert an Ed25519 public key to a did:key identifier
 * Matches backend DIDGenerator.public_key_to_did
 */
export function publicKeyToDid(publicKey: Uint8Array): string {
  if (publicKey.length !== 32) {
    throw new Error('Ed25519 public key must be 32 bytes');
  }

  // Prepend multicodec prefix
  const multicodecKey = new Uint8Array(
    ED25519_MULTICODEC_PREFIX.length + publicKey.length
  );
  multicodecKey.set(ED25519_MULTICODEC_PREFIX);
  multicodecKey.set(publicKey, ED25519_MULTICODEC_PREFIX.length);

  // Encode with base58btc (multibase 'z' prefix)
  const encoded = base58Encode(multicodecKey);

  return `did:key:z${encoded}`;
}

/**
 * Extract the public key from a did:key identifier
 * Matches backend DIDGenerator.did_to_public_key
 */
export function didToPublicKey(did: string): Uint8Array {
  if (!did.startsWith('did:key:z')) {
    throw new Error("Invalid did:key format - must start with 'did:key:z'");
  }

  // Remove prefix and decode
  const encoded = did.slice(9); // Remove "did:key:z"
  const decoded = base58Decode(encoded);

  // Verify multicodec prefix and extract key
  if (
    decoded[0] !== ED25519_MULTICODEC_PREFIX[0] ||
    decoded[1] !== ED25519_MULTICODEC_PREFIX[1]
  ) {
    throw new Error('Invalid multicodec prefix - expected Ed25519');
  }

  const publicKey = decoded.slice(2); // Remove 2-byte prefix

  if (publicKey.length !== 32) {
    throw new Error('Invalid public key length');
  }

  return publicKey;
}

/**
 * Generate a new DID with associated keypair
 */
export function generateDid(): {
  did: string;
  signingKey: Uint8Array;
  verifyKey: Uint8Array;
} {
  const { signingKey, verifyKey } = generateKeyPair();
  const did = publicKeyToDid(verifyKey);

  return { did, signingKey, verifyKey };
}

/**
 * Create a verification method URL for the DID
 * For did:key, the verification method is the DID itself appended
 * with a fragment that is the same as the method-specific identifier
 */
export function createVerificationMethod(did: string): string {
  const methodId = did.split(':').pop(); // Get z6Mk... part
  return `${did}#${methodId}`;
}

/**
 * Sign a message with an Ed25519 signing key
 */
export function signMessage(
  message: Uint8Array,
  signingKey: Uint8Array
): Uint8Array {
  const signedMessage = nacl.sign(message, signingKey);
  // Extract just the signature (first 64 bytes)
  return signedMessage.slice(0, nacl.sign.signatureLength);
}

/**
 * Verify a signature with an Ed25519 public key
 */
export function verifySignature(
  message: Uint8Array,
  signature: Uint8Array,
  publicKey: Uint8Array
): boolean {
  // Prepend signature to message for nacl.sign.open
  const signedMessage = new Uint8Array(signature.length + message.length);
  signedMessage.set(signature);
  signedMessage.set(message, signature.length);

  const result = nacl.sign.open(signedMessage, publicKey);
  return result !== null;
}

/**
 * Sign a message and return base64-encoded signature
 */
export function signMessageBase64(
  message: string | Uint8Array,
  signingKey: Uint8Array
): string {
  const messageBytes =
    typeof message === 'string' ? new TextEncoder().encode(message) : message;
  const signature = signMessage(messageBytes, signingKey);
  return encodeBase64(signature);
}

/**
 * Verify a base64-encoded signature
 */
export function verifySignatureBase64(
  message: string | Uint8Array,
  signatureB64: string,
  publicKey: Uint8Array
): boolean {
  try {
    const messageBytes =
      typeof message === 'string' ? new TextEncoder().encode(message) : message;
    const signature = decodeBase64(signatureB64);
    return verifySignature(messageBytes, signature, publicKey);
  } catch {
    return false;
  }
}

/**
 * Utility functions for encoding
 */
export { encodeBase64, decodeBase64 };
