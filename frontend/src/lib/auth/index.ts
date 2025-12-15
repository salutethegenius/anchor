/**
 * ANCHOR Auth Module
 */

export {
  isWebAuthnSupported,
  isPlatformAuthenticatorAvailable,
  registerPasskey,
  authenticateWithPasskey,
  hasPasskey,
} from './webauthn';
