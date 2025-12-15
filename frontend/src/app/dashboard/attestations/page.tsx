'use client';

import { useEffect, useState } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  FileCheck,
  Loader2,
  CheckCircle,
  XCircle,
  Clock,
  AlertCircle,
} from 'lucide-react';
import { useAccountStore, useVaultStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { AttestationResponse } from '@/lib/api/types';

export default function AttestationsPage() {
  const { accountId } = useAccountStore();
  const { documents, setDocuments, setLoading, isLoading } = useVaultStore();
  const [attestations, setAttestations] = useState<AttestationResponse[]>([]);

  useEffect(() => {
    async function loadData() {
      if (!accountId) return;

      setLoading(true);
      try {
        // Load documents first
        const docList = await api.vault.list(accountId);
        setDocuments(docList.documents);

        // Then load attestations for each document
        const allAttestations: AttestationResponse[] = [];
        for (const doc of docList.documents) {
          if (doc.attestation_count > 0) {
            const docAttestations = await api.vault.attestations(doc.doc_id);
            allAttestations.push(...docAttestations.attestations);
          }
        }
        setAttestations(allAttestations);
      } catch (error) {
        console.error('Failed to load attestations:', error);
      } finally {
        setLoading(false);
      }
    }

    loadData();
  }, [accountId, setDocuments, setLoading]);

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const statusConfig: Record<string, { icon: typeof CheckCircle; color: string; label: string }> = {
    active: { icon: CheckCircle, color: 'text-green-600', label: 'Active' },
    revoked: { icon: XCircle, color: 'text-red-600', label: 'Revoked' },
    expired: { icon: Clock, color: 'text-yellow-600', label: 'Expired' },
    suspended: { icon: AlertCircle, color: 'text-orange-600', label: 'Suspended' },
  };

  const totalAttestations = documents.reduce((sum, doc) => sum + doc.attestation_count, 0);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Attestations</h1>
        <p className="text-muted-foreground">
          Verifiable credentials issued by trusted parties for your documents.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Total Attestations</CardDescription>
            <CardTitle className="text-3xl">{totalAttestations}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Active</CardDescription>
            <CardTitle className="text-3xl text-green-600">
              {attestations.filter(a => a.revocation_status === 'active').length}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardDescription>Documents with Attestations</CardDescription>
            <CardTitle className="text-3xl">
              {documents.filter(d => d.attestation_count > 0).length}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Attestations List */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : attestations.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FileCheck className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No Attestations</h3>
            <p className="text-muted-foreground mb-4">
              Your documents have not yet received any attestations from trusted parties.
            </p>
            <p className="text-sm text-muted-foreground">
              Attestations can be issued by banks, lawyers, notaries, or other authorized entities.
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {attestations.map((attestation) => {
            const status = statusConfig[attestation.revocation_status] || statusConfig.active;
            const StatusIcon = status.icon;
            const doc = documents.find(d => d.doc_id === attestation.document_id);

            return (
              <Card key={attestation.attestation_id}>
                <CardContent className="py-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <div className="w-10 h-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <FileCheck className="w-5 h-5 text-primary" />
                      </div>
                      <div>
                        <p className="font-medium">{attestation.credential_type}</p>
                        <p className="text-sm text-muted-foreground">
                          Issued by: {attestation.issuer_did.slice(0, 30)}...
                        </p>
                        {doc && (
                          <p className="text-xs text-muted-foreground">
                            For: {doc.doc_type}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <div className="text-right">
                        <p className="text-sm text-muted-foreground">
                          Issued {formatDate(attestation.issued_at)}
                        </p>
                        {attestation.expires_at && (
                          <p className="text-xs text-muted-foreground">
                            Expires {formatDate(attestation.expires_at)}
                          </p>
                        )}
                      </div>
                      <Badge variant="outline" className={status.color}>
                        <StatusIcon className="w-3 h-3 mr-1" />
                        {status.label}
                      </Badge>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
