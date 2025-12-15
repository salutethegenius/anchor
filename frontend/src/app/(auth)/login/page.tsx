'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { 
  Shield, 
  ArrowLeft,
  ArrowRight,
  Loader2,
  Fingerprint,
  KeyRound
} from 'lucide-react';
import { toast } from 'sonner';
import { decodeBase64 } from '@/lib/crypto';
import { deriveKey } from '@/lib/crypto/keys';
import { decryptSymmetric, EncryptedPayload, DecryptionError } from '@/lib/crypto/encrypt';
import { api } from '@/lib/api';
import { useAccountStore } from '@/lib/store';

type LoginMethod = 'select' | 'passphrase' | 'passkey';

export default function LoginPage() {
  const router = useRouter();
  const [method, setMethod] = useState<LoginMethod>('select');
  const [passphrase, setPassphrase] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [hydrated, setHydrated] = useState(false);

  const { accountId, encryptedSecretKey, publicKey, setAccount } = useAccountStore();

  // Handle hydration
  useEffect(() => {
    setHydrated(true);
  }, []);

  const handlePassphraseLogin = async () => {
    if (!encryptedSecretKey || !accountId) {
      toast.error('No account found. Please create an account first.');
      return;
    }

    setIsLoading(true);

    try {
      // Parse the stored encrypted key
      const storedData = JSON.parse(encryptedSecretKey);
      const salt = decodeBase64(storedData.salt);
      const encryptedPayload: EncryptedPayload = {
        ciphertext: storedData.ciphertext,
        nonce: storedData.nonce,
        scheme: storedData.scheme,
      };

      // Derive key from passphrase
      let encryptionKey: Uint8Array;
      try {
        encryptionKey = await deriveKey(passphrase, salt);
      } catch (error) {
        console.error('Key derivation failed:', error);
        if (error instanceof Error && error.message.includes('Web Crypto API')) {
          toast.error('Your browser does not support required security features. Please use a modern browser or ensure you are on HTTPS.');
        } else {
          toast.error('Failed to derive encryption key. Please try again.');
        }
        setIsLoading(false);
        return;
      }

      // Try to decrypt the secret key
      try {
        decryptSymmetric(encryptedPayload, encryptionKey);
      } catch (decryptError) {
        // DecryptionError is expected when password is wrong - don't log as error
        if (decryptError instanceof DecryptionError) {
          // Silent failure - this is expected behavior for wrong password
          toast.error('Incorrect passphrase');
        } else {
          // Log unexpected errors
          console.error('Unexpected decryption error:', decryptError);
          toast.error('Failed to decrypt account. Please try again.');
        }
        setIsLoading(false);
        return;
      }

      // Fetch account from backend
      const account = await api.accounts.get(accountId);
      setAccount(account);

      // Update heartbeat
      await api.accounts.heartbeat(accountId);

      toast.success('Welcome back!');
      router.push('/dashboard');
    } catch (error) {
      console.error('Login failed:', error);
      toast.error('Login failed. Please try again.');
    } finally {
      setIsLoading(false);
    }
  };

  const handlePasskeyLogin = async () => {
    if (!accountId) {
      toast.error('No account found');
      return;
    }

    setIsLoading(true);
    
    try {
      // Import dynamically to avoid SSR issues
      const { authenticateWithPasskey } = await import('@/lib/auth/webauthn');
      const result = await authenticateWithPasskey(accountId);
      
      if (result.success) {
        // Fetch account from backend
        const account = await api.accounts.get(accountId);
        setAccount(account);
        
        toast.success('Welcome back!');
        router.push('/dashboard');
      } else {
        toast.error(result.error || 'Passkey authentication failed');
      }
    } catch (error) {
      console.error('Passkey login failed:', error);
      toast.error('Passkey authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  const hasExistingAccount = hydrated && !!accountId && !!encryptedSecretKey;

  // Show loading while hydrating
  if (!hydrated) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-background to-muted flex items-center justify-center p-4">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-background to-muted flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Header */}
        <div className="text-center mb-8">
          <Link href="/" className="inline-flex items-center gap-2 text-muted-foreground hover:text-foreground transition-colors mb-8">
            <ArrowLeft className="w-4 h-4" />
            Back to home
          </Link>
          <div className="flex items-center justify-center gap-2 mb-4">
            <div className="w-10 h-10 rounded-lg bg-primary flex items-center justify-center">
              <Shield className="w-6 h-6 text-primary-foreground" />
            </div>
            <span className="font-bold text-2xl">ANCHOR</span>
          </div>
        </div>

        {/* No Account Found */}
        {!hasExistingAccount && (
          <Card>
            <CardHeader className="text-center">
              <CardTitle>No Account Found</CardTitle>
              <CardDescription>
                No account data found on this device. Please create a new account or 
                restore from your recovery network.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Link href="/create" className="block">
                <Button className="w-full gap-2" size="lg">
                  Create New Account
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </Link>
              <Button variant="outline" className="w-full" disabled>
                Restore from Recovery (Coming Soon)
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Select Login Method */}
        {hasExistingAccount && method === 'select' && (
          <Card>
            <CardHeader className="text-center">
              <CardTitle>Welcome Back</CardTitle>
              <CardDescription>
                Choose how you would like to sign in.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Button 
                variant="outline" 
                className="w-full h-auto py-4 flex items-start gap-3 justify-start"
                onClick={() => setMethod('passphrase')}
              >
                <KeyRound className="w-5 h-5 text-primary mt-0.5" />
                <div className="text-left">
                  <p className="font-medium">Passphrase</p>
                  <p className="text-sm text-muted-foreground font-normal">
                    Enter your encryption passphrase
                  </p>
                </div>
              </Button>

              <Button 
                variant="outline" 
                className="w-full h-auto py-4 flex items-start gap-3 justify-start"
                onClick={handlePasskeyLogin}
              >
                <Fingerprint className="w-5 h-5 text-primary mt-0.5" />
                <div className="text-left">
                  <p className="font-medium">Passkey</p>
                  <p className="text-sm text-muted-foreground font-normal">
                    Use Face ID, Touch ID, or security key
                  </p>
                </div>
              </Button>

              <div className="pt-4 border-t text-center">
                <p className="text-sm text-muted-foreground">
                  Not your account?{' '}
                  <Link href="/create" className="text-primary hover:underline">
                    Create a new one
                  </Link>
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Passphrase Login */}
        {hasExistingAccount && method === 'passphrase' && (
          <Card>
            <CardHeader className="text-center">
              <CardTitle>Enter Passphrase</CardTitle>
              <CardDescription>
                Enter your encryption passphrase to unlock your account.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <label className="text-sm font-medium">Passphrase</label>
                <Input
                  type="password"
                  placeholder="Enter your passphrase..."
                  value={passphrase}
                  onChange={(e) => setPassphrase(e.target.value)}
                  autoComplete="current-password"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && passphrase) {
                      handlePassphraseLogin();
                    }
                  }}
                />
              </div>

              <div className="flex gap-3">
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setMethod('select');
                    setPassphrase('');
                  }}
                >
                  Back
                </Button>
                <Button 
                  className="flex-1 gap-2" 
                  onClick={handlePassphraseLogin}
                  disabled={!passphrase || isLoading}
                >
                  {isLoading ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      Unlocking...
                    </>
                  ) : (
                    <>
                      Unlock
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
