/**
 * ANCHOR WebAuthn/Passkey Integration
 * Client-side helpers for passkey registration and authentication
 */

import {
  startRegistration,
  startAuthentication,
  browserSupportsWebAuthn,
} from '@simplewebauthn/browser';
import { api } from '@/lib/api';

// Use inline types to avoid import issues
interface ApiResponse {
  status?: string;
  [key: string]: unknown;
}

/**
 * Check if WebAuthn is supported in the current browser
 */
export function isWebAuthnSupported(): boolean {
  return browserSupportsWebAuthn();
}

/**
 * Check if the device supports platform authenticators (Touch ID, Face ID, Windows Hello)
 */
export async function isPlatformAuthenticatorAvailable(): Promise<boolean> {
  if (!isWebAuthnSupported()) return false;
  
  try {
    return await PublicKeyCredential.isUserVerifyingPlatformAuthenticatorAvailable();
  } catch {
    return false;
  }
}

/**
 * Register a new passkey for the account
 */
export async function registerPasskey(accountId: string): Promise<{
  success: boolean;
  credentialId?: string;
  error?: string;
}> {
  try {
    // Step 1: Get registration options from server
    const optionsResponse = await api.auth.startRegistration(accountId) as ApiResponse;
    
    // Check if registration is not yet implemented
    if (optionsResponse.status === 'not_implemented') {
      return {
        success: false,
        error: 'WebAuthn registration not yet implemented on server',
      };
    }

    // Step 2: Create credential with browser
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const credential = await startRegistration({ optionsJSON: optionsResponse as any });

    // Step 3: Send credential to server for verification
    const verificationResponse = await api.auth.completeRegistration({
      account_id: accountId,
      credential_id: credential.id,
      public_key: credential.response.publicKey || '',
      attestation_object: credential.response.attestationObject,
      client_data_json: credential.response.clientDataJSON,
    }) as ApiResponse;

    if (verificationResponse.status === 'not_implemented') {
      return {
        success: false,
        error: 'WebAuthn registration not yet implemented on server',
      };
    }

    return {
      success: true,
      credentialId: credential.id,
    };
  } catch (error) {
    console.error('Passkey registration failed:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Registration failed',
    };
  }
}

/**
 * Authenticate with a passkey
 */
export async function authenticateWithPasskey(accountId: string): Promise<{
  success: boolean;
  token?: string;
  error?: string;
}> {
  try {
    // Step 1: Get authentication options from server
    const optionsResponse = await api.auth.startAuthentication(accountId) as ApiResponse;
    
    // Check if authentication is not yet implemented
    if (optionsResponse.status === 'not_implemented') {
      return {
        success: false,
        error: 'WebAuthn authentication not yet implemented on server',
      };
    }

    // Step 2: Authenticate with browser
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const credential = await startAuthentication({ optionsJSON: optionsResponse as any });

    // Step 3: Send assertion to server for verification
    const verificationResponse = await api.auth.completeAuthentication({
      account_id: accountId,
      credential_id: credential.id,
      authenticator_data: credential.response.authenticatorData,
      signature: credential.response.signature,
      client_data_json: credential.response.clientDataJSON,
    }) as ApiResponse;

    if (verificationResponse.status === 'not_implemented') {
      return {
        success: false,
        error: 'WebAuthn authentication not yet implemented on server',
      };
    }

    return {
      success: true,
      // Token would be returned from a real implementation
    };
  } catch (error) {
    console.error('Passkey authentication failed:', error);
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Authentication failed',
    };
  }
}

/**
 * Check if an account has a registered passkey
 */
export async function hasPasskey(accountId: string): Promise<boolean> {
  // This would need a backend endpoint to check
  // For now, return false as placeholder
  void accountId;
  return false;
}
