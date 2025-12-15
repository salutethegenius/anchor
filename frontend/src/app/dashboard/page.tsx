'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  FolderLock,
  FileCheck,
  Users,
  Activity,
  ArrowRight,
  Shield,
  Clock,
  Plus,
} from 'lucide-react';
import { useAccountStore, useVaultStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { AccountStatusResponse } from '@/lib/api/types';

export default function DashboardPage() {
  const { account, accountId } = useAccountStore();
  const { documents, setDocuments, setLoading } = useVaultStore();
  const [accountStatus, setAccountStatus] = useState<AccountStatusResponse | null>(null);

  useEffect(() => {
    async function loadData() {
      if (!accountId) return;
      
      setLoading(true);
      try {
        // Fetch account status and documents in parallel
        const [status, docList] = await Promise.all([
          api.accounts.status(accountId),
          api.vault.list(accountId),
        ]);
        
        setAccountStatus(status);
        setDocuments(docList.documents);
      } catch (error) {
        console.error('Failed to load dashboard data:', error);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [accountId, setDocuments, setLoading]);

  const statusColors: Record<string, string> = {
    active: 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400',
    watch: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-400',
    suspended: 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400',
    in_succession: 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400',
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <p className="text-muted-foreground">
          Welcome to your sovereign digital account for The Bahamas.
        </p>
      </div>

      {/* Status Card */}
      <Card>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-lg">Account Status</CardTitle>
            <Badge className={statusColors[account?.status || 'active']}>
              {account?.status?.toUpperCase() || 'ACTIVE'}
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Shield className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">DID</p>
                <p className="text-sm font-mono truncate max-w-[180px]" title={account?.did}>
                  {account?.did ? `${account.did.slice(0, 24)}...` : 'Loading...'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Clock className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Last Activity</p>
                <p className="text-sm font-medium">
                  {account?.last_heartbeat ? formatDate(account.last_heartbeat) : 'Loading...'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                <Activity className="w-5 h-5 text-primary" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Days Inactive</p>
                <p className="text-sm font-medium">
                  {accountStatus?.days_inactive ?? 0} days
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Documents</CardDescription>
            <CardTitle className="text-3xl">{documents.length}</CardTitle>
          </CardHeader>
          <CardContent>
            <Link href="/dashboard/vault">
              <Button variant="ghost" size="sm" className="gap-1 -ml-2">
                View Vault
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Attestations</CardDescription>
            <CardTitle className="text-3xl">
              {documents.reduce((sum, doc) => sum + doc.attestation_count, 0)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Link href="/dashboard/attestations">
              <Button variant="ghost" size="sm" className="gap-1 -ml-2">
                View All
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Recovery Network</CardDescription>
            <CardTitle className="text-3xl">
              {(accountStatus?.recovery_graph_summary?.beneficiaries || 0) +
                (accountStatus?.recovery_graph_summary?.verifiers || 0) +
                (accountStatus?.recovery_graph_summary?.guardians || 0)}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <Link href="/dashboard/recovery">
              <Button variant="ghost" size="sm" className="gap-1 -ml-2">
                Manage
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Link href="/dashboard/vault">
            <Card className="hover:border-primary/50 transition-colors cursor-pointer">
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Plus className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">Add Document</p>
                    <p className="text-sm text-muted-foreground">
                      Upload to your encrypted vault
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href="/dashboard/recovery">
            <Card className="hover:border-primary/50 transition-colors cursor-pointer">
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                    <Users className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">Add Recovery Contact</p>
                    <p className="text-sm text-muted-foreground">
                      Set up your recovery network
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>

          <Link href="/dashboard/settings">
            <Card className="hover:border-primary/50 transition-colors cursor-pointer">
              <CardContent className="pt-6">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 rounded-lg bg-primary/10 flex items-center justify-center">
                    <FileCheck className="w-6 h-6 text-primary" />
                  </div>
                  <div>
                    <p className="font-medium">Setup Passkey</p>
                    <p className="text-sm text-muted-foreground">
                      Enable biometric login
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>
          </Link>
        </div>
      </div>

      {/* Recent Documents */}
      {documents.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Recent Documents</h2>
            <Link href="/dashboard/vault">
              <Button variant="ghost" size="sm" className="gap-1">
                View All
                <ArrowRight className="w-4 h-4" />
              </Button>
            </Link>
          </div>
          <div className="grid gap-3">
            {documents.slice(0, 3).map((doc) => (
              <Card key={doc.doc_id}>
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-lg bg-muted flex items-center justify-center">
                        <FolderLock className="w-5 h-5 text-muted-foreground" />
                      </div>
                      <div>
                        <p className="font-medium capitalize">{doc.doc_type}</p>
                        <p className="text-sm text-muted-foreground">
                          Added {formatDate(doc.created_at)}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {doc.attestation_count > 0 && (
                        <Badge variant="secondary">
                          {doc.attestation_count} attestation{doc.attestation_count !== 1 ? 's' : ''}
                        </Badge>
                      )}
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
