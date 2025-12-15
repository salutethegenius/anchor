'use client';

import { useState, useEffect } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import {
  Fingerprint,
  Shield,
  Key,
  Copy,
  Check,
  AlertCircle,
  Loader2,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAccountStore } from '@/lib/store';
import { 
  isWebAuthnSupported, 
  isPlatformAuthenticatorAvailable,
  registerPasskey,
} from '@/lib/auth/webauthn';

export default function SettingsPage() {
  const { account, accountId, publicKey } = useAccountStore();
  const [copied, setCopied] = useState<string | null>(null);
  const [webAuthnSupported, setWebAuthnSupported] = useState(false);
  const [platformAuthAvailable, setPlatformAuthAvailable] = useState(false);
  const [isRegistering, setIsRegistering] = useState(false);

  useEffect(() => {
    // Check WebAuthn support
    setWebAuthnSupported(isWebAuthnSupported());
    isPlatformAuthenticatorAvailable().then(setPlatformAuthAvailable);
  }, []);

  const handleCopy = async (text: string, id: string) => {
    await navigator.clipboard.writeText(text);
    setCopied(id);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopied(null), 2000);
  };

  const handleRegisterPasskey = async () => {
    if (!accountId) return;

    setIsRegistering(true);
    try {
      const result = await registerPasskey(accountId);
      
      if (result.success) {
        toast.success('Passkey registered successfully!');
      } else {
        toast.error(result.error || 'Failed to register passkey');
      }
    } catch (error) {
      console.error('Passkey registration error:', error);
      toast.error('Failed to register passkey');
    } finally {
      setIsRegistering(false);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account settings and security preferences.
        </p>
      </div>

      {/* Account Information */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Account Information
          </CardTitle>
          <CardDescription>
            Your sovereign digital identity details.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4">
            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Account ID</label>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-2 bg-muted rounded text-sm font-mono">
                  {accountId || 'Loading...'}
                </code>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => accountId && handleCopy(accountId, 'accountId')}
                >
                  {copied === 'accountId' ? (
                    <Check className="w-4 h-4 text-green-500" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">DID (Decentralized Identifier)</label>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-2 bg-muted rounded text-sm font-mono truncate">
                  {account?.did || 'Loading...'}
                </code>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => account?.did && handleCopy(account.did, 'did')}
                >
                  {copied === 'did' ? (
                    <Check className="w-4 h-4 text-green-500" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>

            <div className="space-y-1">
              <label className="text-sm text-muted-foreground">Public Key</label>
              <div className="flex items-center gap-2">
                <code className="flex-1 p-2 bg-muted rounded text-sm font-mono truncate">
                  {publicKey || 'Loading...'}
                </code>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => publicKey && handleCopy(publicKey, 'publicKey')}
                >
                  {copied === 'publicKey' ? (
                    <Check className="w-4 h-4 text-green-500" />
                  ) : (
                    <Copy className="w-4 h-4" />
                  )}
                </Button>
              </div>
            </div>

            <Separator />

            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">Status</label>
                <div>
                  <Badge
                    variant="secondary"
                    className={
                      account?.status === 'active'
                        ? 'bg-green-100 text-green-800'
                        : 'bg-yellow-100 text-yellow-800'
                    }
                  >
                    {account?.status?.toUpperCase() || 'LOADING'}
                  </Badge>
                </div>
              </div>
              <div className="space-y-1">
                <label className="text-sm text-muted-foreground">Created</label>
                <p className="text-sm">
                  {account?.created_at ? formatDate(account.created_at) : 'Loading...'}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Passkey Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Fingerprint className="w-5 h-5" />
            Passkey Authentication
          </CardTitle>
          <CardDescription>
            Use Face ID, Touch ID, or a security key for quick and secure login.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {!webAuthnSupported ? (
            <div className="flex items-center gap-3 p-4 rounded-lg bg-destructive/10 border border-destructive/20">
              <AlertCircle className="w-5 h-5 text-destructive" />
              <div>
                <p className="font-medium text-destructive">Not Supported</p>
                <p className="text-sm text-muted-foreground">
                  Your browser does not support WebAuthn. Please use a modern browser.
                </p>
              </div>
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between p-4 rounded-lg border">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Fingerprint className="w-5 h-5 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">Platform Authenticator</p>
                    <p className="text-sm text-muted-foreground">
                      {platformAuthAvailable
                        ? 'Face ID, Touch ID, or Windows Hello'
                        : 'Not available on this device'}
                    </p>
                  </div>
                </div>
                <Button
                  onClick={handleRegisterPasskey}
                  disabled={isRegistering}
                >
                  {isRegistering ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Registering...
                    </>
                  ) : (
                    'Register'
                  )}
                </Button>
              </div>

              <div className="flex items-center justify-between p-4 rounded-lg border">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                    <Key className="w-5 h-5 text-muted-foreground" />
                  </div>
                  <div>
                    <p className="font-medium">Security Key</p>
                    <p className="text-sm text-muted-foreground">
                      YubiKey or other FIDO2 security key
                    </p>
                  </div>
                </div>
                <Button variant="outline" onClick={handleRegisterPasskey} disabled={isRegistering}>
                  Register
                </Button>
              </div>
            </>
          )}

          <div className="p-4 rounded-lg bg-muted">
            <p className="text-sm text-muted-foreground">
              <strong>Note:</strong> Passkey authentication provides phishing-resistant 
              security. Your biometric data never leaves your device.
            </p>
          </div>
        </CardContent>
      </Card>

      {/* Security Settings */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Shield className="w-5 h-5" />
            Security
          </CardTitle>
          <CardDescription>
            Manage your account security settings.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between p-4 rounded-lg border">
            <div>
              <p className="font-medium">Change Passphrase</p>
              <p className="text-sm text-muted-foreground">
                Update your encryption passphrase
              </p>
            </div>
            <Button variant="outline" disabled>
              Coming Soon
            </Button>
          </div>

          <div className="flex items-center justify-between p-4 rounded-lg border">
            <div>
              <p className="font-medium">Export Recovery Kit</p>
              <p className="text-sm text-muted-foreground">
                Download encrypted backup of your keys
              </p>
            </div>
            <Button variant="outline" disabled>
              Coming Soon
            </Button>
          </div>

          <div className="flex items-center justify-between p-4 rounded-lg border border-destructive/20">
            <div>
              <p className="font-medium text-destructive">Delete Account</p>
              <p className="text-sm text-muted-foreground">
                Permanently delete your account and all data
              </p>
            </div>
            <Button variant="destructive" disabled>
              Delete
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
