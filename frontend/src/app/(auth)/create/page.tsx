'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { 
  Shield, 
  Key, 
  CheckCircle2,
  Loader2,
  ArrowLeft,
  ArrowRight,
  Lock,
  Fingerprint
} from 'lucide-react';
import { toast } from 'sonner';
import { generateDid, encodeBase64 } from '@/lib/crypto';
import { deriveKeyWithNewSalt } from '@/lib/crypto/keys';
import { encryptSymmetric } from '@/lib/crypto/encrypt';
import { api, ApiClientError } from '@/lib/api';
import { useAccountStore } from '@/lib/store';

type Step = 'intro' | 'passphrase' | 'generating' | 'complete';

export default function CreateAccountPage() {
  const router = useRouter();
  const [step, setStep] = useState<Step>('intro');
  const [passphrase, setPassphrase] = useState('');
  const [confirmPassphrase, setConfirmPassphrase] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [accountData, setAccountData] = useState<{
    did: string;
    accountId: string;
  } | null>(null);

  const { setAccount, setKeys } = useAccountStore();

  const handleCreateAccount = async () => {
    if (passphrase !== confirmPassphrase) {
      toast.error('Passphrases do not match');
      return;
    }

    if (passphrase.length < 12) {
      toast.error('Passphrase must be at least 12 characters');
      return;
    }

    setStep('generating');
    setIsLoading(true);

    try {
      // Step 1: Generate keypair and DID
      const { did, signingKey, verifyKey } = generateDid();

      // Step 2: Derive encryption key from passphrase
      const { key: encryptionKey, salt } = await deriveKeyWithNewSalt(passphrase);

      // Step 3: Encrypt the signing key with the derived key
      const encryptedKey = encryptSymmetric(signingKey, encryptionKey);
      const encryptedKeyWithSalt = JSON.stringify({
        ...encryptedKey,
        salt: encodeBase64(salt),
      });

      // Step 4: Create account on backend with public key
      const publicKeyB64 = encodeBase64(verifyKey);
      const account = await api.accounts.create({
        owner_pubkey: publicKeyB64,
      });

      // Step 5: Store in local state
      setAccount(account);
      setKeys(publicKeyB64, encryptedKeyWithSalt);

      setAccountData({
        did,
        accountId: account.account_id,
      });

      setStep('complete');
      toast.success('Account created successfully!');
    } catch (error) {
      console.error('Account creation failed:', error);
      
      // Provide more detailed error messages
      let errorMessage = 'Failed to create account. Please try again.';
      if (error instanceof Error) {
        console.error('Error details:', {
          message: error.message,
          stack: error.stack,
          name: error.name,
        });
        
        // Check for specific error types
        if (error.message.includes('Invalid public key')) {
          errorMessage = 'Invalid public key format. Please try again.';
        } else if (error.message.includes('already exists')) {
          errorMessage = 'An account with this public key already exists.';
        } else if (error.message.includes('network') || error.message.includes('fetch')) {
          errorMessage = 'Network error. Please check your connection and try again.';
        } else {
          errorMessage = `Error: ${error.message}`;
        }
      } else if (error instanceof ApiClientError) {
        // Handle API client errors with detail
        errorMessage = error.detail || error.message;
      } else if (typeof error === 'object' && error !== null && 'detail' in error) {
        errorMessage = `Error: ${(error as { detail: string }).detail}`;
      }
      
      toast.error(errorMessage);
      setStep('passphrase');
    } finally {
      setIsLoading(false);
    }
  };

  const handleContinue = () => {
    router.push('/dashboard');
  };

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

        {/* Step: Intro */}
        {step === 'intro' && (
          <Card>
            <CardHeader className="text-center">
              <CardTitle>Create Your Anchor</CardTitle>
              <CardDescription>
                Set up your sovereign digital account built for Bahamians in a few simple steps.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="flex items-start gap-3 p-3 rounded-lg bg-muted">
                  <Key className="w-5 h-5 text-primary mt-0.5" />
                  <div>
                    <p className="font-medium text-sm">Generate Keys</p>
                    <p className="text-sm text-muted-foreground">
                      We create a unique cryptographic keypair for your identity.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-lg bg-muted">
                  <Lock className="w-5 h-5 text-primary mt-0.5" />
                  <div>
                    <p className="font-medium text-sm">Secure with Passphrase</p>
                    <p className="text-sm text-muted-foreground">
                      Your keys are encrypted with a passphrase you choose.
                    </p>
                  </div>
                </div>
                <div className="flex items-start gap-3 p-3 rounded-lg bg-muted">
                  <Fingerprint className="w-5 h-5 text-primary mt-0.5" />
                  <div>
                    <p className="font-medium text-sm">Add Passkey (Optional)</p>
                    <p className="text-sm text-muted-foreground">
                      Enable Face ID, Touch ID, or security key for quick access.
                    </p>
                  </div>
                </div>
              </div>

              <Button 
                className="w-full gap-2" 
                size="lg"
                onClick={() => setStep('passphrase')}
              >
                Get Started
                <ArrowRight className="w-4 h-4" />
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Step: Passphrase */}
        {step === 'passphrase' && (
          <Card>
            <CardHeader className="text-center">
              <CardTitle>Create Your Passphrase</CardTitle>
              <CardDescription>
                This passphrase encrypts your private key. Write it down and keep it safe.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-4">
                <div className="space-y-2">
                  <label className="text-sm font-medium">Passphrase</label>
                  <Input
                    type="password"
                    placeholder="Enter a strong passphrase..."
                    value={passphrase}
                    onChange={(e) => setPassphrase(e.target.value)}
                    autoComplete="new-password"
                  />
                  <p className="text-xs text-muted-foreground">
                    Minimum 12 characters. Use a mix of words, numbers, and symbols.
                  </p>
                </div>
                <div className="space-y-2">
                  <label className="text-sm font-medium">Confirm Passphrase</label>
                  <Input
                    type="password"
                    placeholder="Confirm your passphrase..."
                    value={confirmPassphrase}
                    onChange={(e) => setConfirmPassphrase(e.target.value)}
                    autoComplete="new-password"
                  />
                </div>
              </div>

              <div className="p-4 rounded-lg bg-destructive/10 border border-destructive/20">
                <p className="text-sm font-medium text-destructive">Important</p>
                <p className="text-sm text-muted-foreground mt-1">
                  There is no password reset. If you forget your passphrase, 
                  you will need your recovery network to regain access.
                </p>
              </div>

              <div className="flex gap-3">
                <Button 
                  variant="outline" 
                  onClick={() => setStep('intro')}
                >
                  Back
                </Button>
                <Button 
                  className="flex-1 gap-2" 
                  onClick={handleCreateAccount}
                  disabled={!passphrase || !confirmPassphrase || passphrase !== confirmPassphrase}
                >
                  Create Account
                  <ArrowRight className="w-4 h-4" />
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step: Generating */}
        {step === 'generating' && (
          <Card>
            <CardHeader className="text-center">
              <CardTitle>Creating Your Account</CardTitle>
              <CardDescription>
                Generating your cryptographic identity...
              </CardDescription>
            </CardHeader>
            <CardContent className="py-12">
              <div className="flex flex-col items-center gap-4">
                <Loader2 className="w-12 h-12 text-primary animate-spin" />
                <div className="text-center">
                  <p className="text-sm text-muted-foreground">
                    Generating keypair and encrypting...
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Step: Complete */}
        {step === 'complete' && accountData && (
          <Card>
            <CardHeader className="text-center">
              <div className="w-16 h-16 rounded-full bg-green-100 dark:bg-green-900/20 flex items-center justify-center mx-auto mb-4">
                <CheckCircle2 className="w-8 h-8 text-green-600" />
              </div>
              <CardTitle>Account Created!</CardTitle>
              <CardDescription>
                Your sovereign digital identity for The Bahamas is ready.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="p-4 rounded-lg bg-muted space-y-3">
                <div>
                  <p className="text-xs text-muted-foreground">Your DID</p>
                  <p className="text-sm font-mono break-all">{accountData.did}</p>
                </div>
                <div>
                  <p className="text-xs text-muted-foreground">Account ID</p>
                  <p className="text-sm font-mono">{accountData.accountId}</p>
                </div>
              </div>

              <div className="p-4 rounded-lg bg-primary/5 border">
                <p className="text-sm font-medium">Next Steps</p>
                <ul className="text-sm text-muted-foreground mt-2 space-y-1">
                  <li>• Add documents to your vault</li>
                  <li>• Set up your recovery network</li>
                  <li>• Configure passkey for quick access</li>
                </ul>
              </div>

              <Button 
                className="w-full gap-2" 
                size="lg"
                onClick={handleContinue}
              >
                Go to Dashboard
                <ArrowRight className="w-4 h-4" />
              </Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
