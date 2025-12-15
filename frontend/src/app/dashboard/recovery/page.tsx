'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Users,
  Plus,
  UserPlus,
  Shield,
  Eye,
  Heart,
  Loader2,
  MoreVertical,
  Trash2,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAccountStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { RecoveryRoleResponse, RoleType } from '@/lib/api/types';

const roleConfig: Record<RoleType, { icon: typeof Heart; label: string; description: string; color: string }> = {
  primary_owner: { 
    icon: Shield, 
    label: 'Owner', 
    description: 'Full account access',
    color: 'bg-primary/10 text-primary',
  },
  beneficiary: { 
    icon: Heart, 
    label: 'Beneficiary', 
    description: 'Receives access during succession',
    color: 'bg-pink-100 text-pink-700 dark:bg-pink-900/20 dark:text-pink-400',
  },
  verifier: { 
    icon: Eye, 
    label: 'Verifier', 
    description: 'Confirms succession claims',
    color: 'bg-blue-100 text-blue-700 dark:bg-blue-900/20 dark:text-blue-400',
  },
  guardian: { 
    icon: Shield, 
    label: 'Guardian', 
    description: 'Assists with account recovery',
    color: 'bg-green-100 text-green-700 dark:bg-green-900/20 dark:text-green-400',
  },
};

export default function RecoveryPage() {
  const { accountId, account } = useAccountStore();
  const [roles, setRoles] = useState<RecoveryRoleResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isAddOpen, setIsAddOpen] = useState(false);
  const [isAdding, setIsAdding] = useState(false);
  const [newRoleType, setNewRoleType] = useState<RoleType>('beneficiary');
  const [targetDid, setTargetDid] = useState('');

  useEffect(() => {
    async function loadRoles() {
      if (!accountId) return;

      setIsLoading(true);
      try {
        const response = await api.recovery.listRoles(accountId);
        setRoles(response.roles || []);
      } catch (error) {
        console.error('Failed to load recovery roles:', error);
      } finally {
        setIsLoading(false);
      }
    }

    loadRoles();
  }, [accountId]);

  const handleAddRole = async () => {
    if (!accountId || !targetDid) return;

    setIsAdding(true);
    try {
      // First, look up the target account by DID
      const targetAccount = await api.accounts.getByDid(targetDid);

      // Generate a placeholder signature
      // In production, this would be a real Ed25519 signature using the unlocked private key
      const timestamp = new Date().toISOString();
      const signatureData = `role:${newRoleType}:target:${targetAccount.account_id}:time:${timestamp}`;
      // For demo purposes, use a base64-encoded hash as a placeholder signature
      const encoder = new TextEncoder();
      const data = encoder.encode(signatureData);
      const hashBuffer = await crypto.subtle.digest('SHA-256', data);
      const hashArray = new Uint8Array(hashBuffer);
      const ownerSignature = btoa(String.fromCharCode(...hashArray));

      // Create the recovery role
      const newRole = await api.recovery.createRole(accountId, {
        target_id: targetAccount.account_id,
        role_type: newRoleType,
        owner_signature: ownerSignature,
      });

      setRoles([...roles, newRole]);
      toast.success('Recovery contact added successfully');
      setIsAddOpen(false);
      setTargetDid('');
    } catch (error) {
      console.error('Failed to add role:', error);
      toast.error('Failed to add recovery contact. Make sure the DID is correct.');
    } finally {
      setIsAdding(false);
    }
  };

  const handleDeleteRole = async (roleId: string) => {
    try {
      await api.recovery.deleteRole(roleId);
      setRoles(roles.filter(r => r.role_id !== roleId));
      toast.success('Recovery contact removed');
    } catch (error) {
      console.error('Failed to delete role:', error);
      toast.error('Failed to remove recovery contact');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  // Group roles by type
  const beneficiaries = roles.filter(r => r.role_type === 'beneficiary');
  const verifiers = roles.filter(r => r.role_type === 'verifier');
  const guardians = roles.filter(r => r.role_type === 'guardian');

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Recovery Network</h1>
          <p className="text-muted-foreground">
            Set up trusted contacts for account recovery and succession.
          </p>
        </div>
        <Dialog open={isAddOpen} onOpenChange={setIsAddOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              Add Contact
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Recovery Contact</DialogTitle>
              <DialogDescription>
                Add a trusted person to your recovery network. They will need an ANCHOR account.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Role Type</label>
                <div className="grid grid-cols-3 gap-2">
                  {(['beneficiary', 'verifier', 'guardian'] as RoleType[]).map((type) => {
                    const config = roleConfig[type];
                    const Icon = config.icon;
                    return (
                      <button
                        key={type}
                        onClick={() => setNewRoleType(type)}
                        className={`p-3 rounded-lg border text-center transition-colors ${
                          newRoleType === type
                            ? 'border-primary bg-primary/10'
                            : 'hover:border-primary/50'
                        }`}
                      >
                        <Icon className="w-6 h-6 mx-auto mb-1" />
                        <p className="text-sm font-medium">{config.label}</p>
                      </button>
                    );
                  })}
                </div>
                <p className="text-xs text-muted-foreground mt-2">
                  {roleConfig[newRoleType].description}
                </p>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">Contact&apos;s DID</label>
                <Input
                  placeholder="did:key:z6Mk..."
                  value={targetDid}
                  onChange={(e) => setTargetDid(e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  Enter the DID of the person you want to add. They can find their DID in their account settings.
                </p>
              </div>

              <Button
                className="w-full gap-2"
                onClick={handleAddRole}
                disabled={!targetDid || isAdding}
              >
                {isAdding ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Adding...
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4" />
                    Add Contact
                  </>
                )}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Beneficiaries</CardDescription>
            <CardTitle className="text-3xl">{beneficiaries.length}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Will receive access during succession
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Verifiers</CardDescription>
            <CardTitle className="text-3xl">{verifiers.length}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Must confirm succession claims
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Guardians</CardDescription>
            <CardTitle className="text-3xl">{guardians.length}</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Can assist with account recovery
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Roles List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : roles.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <Users className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No Recovery Contacts</h3>
            <p className="text-muted-foreground mb-4">
              Add trusted people to your recovery network to enable account recovery and succession.
            </p>
            <Button onClick={() => setIsAddOpen(true)} className="gap-2">
              <Plus className="w-4 h-4" />
              Add Your First Contact
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {roles.map((role) => {
            const config = roleConfig[role.role_type];
            const Icon = config.icon;

            return (
              <Card key={role.role_id}>
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${config.color}`}>
                        <Icon className="w-5 h-5" />
                      </div>
                      <div>
                        <div className="flex items-center gap-2">
                          <p className="font-medium">{config.label}</p>
                          <Badge variant="outline">Priority {role.priority}</Badge>
                        </div>
                        <p className="text-sm text-muted-foreground font-mono">
                          {role.target_id.slice(0, 8)}...{role.target_id.slice(-4)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <p className="text-sm text-muted-foreground">
                        Added {formatDate(role.created_at)}
                      </p>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => handleDeleteRole(role.role_id)}
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Remove
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Info Card */}
      <Card className="bg-muted/50">
        <CardHeader>
          <CardTitle className="text-base">How Recovery Works</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            <strong>Inactivity Detection:</strong> If you don&apos;t log in for an extended period, 
            your account enters &quot;watch&quot; mode and your verifiers are notified.
          </p>
          <p>
            <strong>Succession Claims:</strong> Beneficiaries can initiate a succession claim 
            with legal documentation. Verifiers must confirm the claim.
          </p>
          <p>
            <strong>Staged Access:</strong> Once verified, beneficiaries receive gradual access 
            to your vault contents based on priority.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
