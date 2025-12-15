'use client';

import { useEffect, useState, useCallback } from 'react';
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
  FolderLock,
  Plus,
  Upload,
  MoreVertical,
  FileText,
  Trash2,
  Download,
  Shield,
  Loader2,
  Search,
  Filter,
} from 'lucide-react';
import { toast } from 'sonner';
import { useAccountStore, useVaultStore } from '@/lib/store';
import { api } from '@/lib/api';
import type { DocumentType, DocumentResponse } from '@/lib/api/types';
import { encryptForVault, generateContentHash, generateKey, encodeBase64 } from '@/lib/crypto';

const documentTypes: { value: DocumentType; label: string }[] = [
  { value: 'passport', label: 'Bahamian Passport' },
  { value: 'nib', label: 'NIB Card' },
  { value: 'voter', label: 'Voter ID' },
  { value: 'insurance', label: 'Insurance' },
  { value: 'will', label: 'Will' },
  { value: 'property', label: 'Property' },
  { value: 'contract', label: 'Contract' },
  { value: 'medical', label: 'Medical' },
  { value: 'education', label: 'Education' },
  { value: 'other', label: 'Other' },
];

const documentTypeIcons: Record<DocumentType, string> = {
  passport: '🛂',
  nib: '🪪',
  voter: '🗳️',
  insurance: '🏥',
  will: '📜',
  property: '🏠',
  contract: '📝',
  medical: '⚕️',
  education: '🎓',
  other: '📄',
};

export default function VaultPage() {
  const { accountId } = useAccountStore();
  const { documents, setDocuments, addDocument, removeDocument, isLoading, setLoading } = useVaultStore();
  
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<DocumentType | 'all'>('all');
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadDocType, setUploadDocType] = useState<DocumentType>('passport');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);

  const loadDocuments = useCallback(async () => {
    if (!accountId) return;
    
    setLoading(true);
    try {
      const docList = await api.vault.list(accountId);
      setDocuments(docList.documents);
    } catch (error) {
      console.error('Failed to load documents:', error);
      toast.error('Failed to load documents');
    } finally {
      setLoading(false);
    }
  }, [accountId, setDocuments, setLoading]);

  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const handleUpload = async () => {
    if (!selectedFile || !accountId) return;

    setIsUploading(true);

    try {
      // Read file content
      const fileBuffer = await selectedFile.arrayBuffer();
      const fileData = new Uint8Array(fileBuffer);

      // Generate document encryption key
      const documentKey = generateKey();

      // Encrypt the file content
      const { encryptedBlob, encryptionMeta } = encryptForVault(fileData, documentKey);

      // Generate content hash
      const contentHash = await generateContentHash(encryptedBlob);

      // Create a reference (in a real app, this would upload to S3/blob storage)
      const ciphertextRef = `vault/${accountId}/${Date.now()}-${selectedFile.name}.enc`;

      // Store document metadata on backend
      const document = await api.vault.create(accountId, {
        doc_type: uploadDocType,
        ciphertext_ref: ciphertextRef,
        encryption_meta: encryptionMeta,
        content_hash: contentHash,
        file_meta: {
          original_name: selectedFile.name,
          size: selectedFile.size,
          type: selectedFile.type,
        },
      });

      addDocument(document);
      toast.success('Document uploaded successfully!');
      setIsUploadOpen(false);
      setSelectedFile(null);
      setUploadDocType('passport');
    } catch (error) {
      console.error('Upload failed:', error);
      toast.error('Failed to upload document');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (docId: string) => {
    try {
      await api.vault.delete(docId);
      removeDocument(docId);
      toast.success('Document deleted');
    } catch (error) {
      console.error('Delete failed:', error);
      toast.error('Failed to delete document');
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  // Filter documents
  const filteredDocuments = documents.filter((doc) => {
    const matchesType = filterType === 'all' || doc.doc_type === filterType;
    const matchesSearch = searchQuery === '' || 
      doc.doc_type.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (doc.file_meta as { original_name?: string })?.original_name?.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesType && matchesSearch;
  });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Vault</h1>
          <p className="text-muted-foreground">
            Your encrypted document storage for Bahamian identity documents. 
            All files are encrypted client-side before upload.
          </p>
        </div>
        <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
          <DialogTrigger asChild>
            <Button className="gap-2">
              <Plus className="w-4 h-4" />
              Add Document
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Upload Document</DialogTitle>
              <DialogDescription>
                Upload your Bahamian documents (Passport, NIB Card, Voter ID, etc.). 
                Your document will be encrypted before upload. Only you can decrypt it.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <label className="text-sm font-medium">Document Type</label>
                <div className="grid grid-cols-5 gap-2">
                  {documentTypes.map((type) => (
                    <button
                      key={type.value}
                      onClick={() => setUploadDocType(type.value)}
                      className={`p-3 rounded-lg border text-center transition-colors ${
                        uploadDocType === type.value
                          ? 'border-primary bg-primary/10'
                          : 'hover:border-primary/50'
                      }`}
                    >
                      <span className="text-2xl">{documentTypeIcons[type.value]}</span>
                      <p className="text-xs mt-1 truncate">{type.label}</p>
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                <label className="text-sm font-medium">File</label>
                <div 
                  className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
                    selectedFile ? 'border-primary bg-primary/5' : 'hover:border-primary/50'
                  }`}
                >
                  {selectedFile ? (
                    <div className="space-y-2">
                      <FileText className="w-10 h-10 mx-auto text-primary" />
                      <p className="font-medium">{selectedFile.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {formatFileSize(selectedFile.size)}
                      </p>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => setSelectedFile(null)}
                      >
                        Remove
                      </Button>
                    </div>
                  ) : (
                    <label className="cursor-pointer">
                      <Upload className="w-10 h-10 mx-auto text-muted-foreground mb-2" />
                      <p className="text-sm font-medium">Click to upload</p>
                      <p className="text-xs text-muted-foreground mt-1">
                        PDF, images, or documents up to 10MB (Bahamian documents preferred)
                      </p>
                      <input
                        type="file"
                        className="hidden"
                        onChange={handleFileSelect}
                        accept=".pdf,.png,.jpg,.jpeg,.doc,.docx"
                      />
                    </label>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 p-3 rounded-lg bg-muted">
                <Shield className="w-4 h-4 text-primary" />
                <p className="text-sm text-muted-foreground">
                  End-to-end encrypted with XSalsa20-Poly1305
                </p>
              </div>

              <Button 
                className="w-full gap-2" 
                onClick={handleUpload}
                disabled={!selectedFile || isUploading}
              >
                {isUploading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Encrypting & Uploading...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4" />
                    Upload Document
                  </>
                )}
              </Button>
            </div>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-4">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search documents..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" className="gap-2">
              <Filter className="w-4 h-4" />
              {filterType === 'all' ? 'All Types' : documentTypes.find(t => t.value === filterType)?.label}
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem onClick={() => setFilterType('all')}>
              All Types
            </DropdownMenuItem>
            {documentTypes.map((type) => (
              <DropdownMenuItem 
                key={type.value}
                onClick={() => setFilterType(type.value)}
              >
                {documentTypeIcons[type.value]} {type.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Document Grid */}
      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
        </div>
      ) : filteredDocuments.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <FolderLock className="w-12 h-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No Documents</h3>
            <p className="text-muted-foreground mb-4">
              {searchQuery || filterType !== 'all'
                ? 'No documents match your search criteria.'
                : 'Your vault is empty. Add your first document to get started.'}
            </p>
            {!searchQuery && filterType === 'all' && (
              <Button onClick={() => setIsUploadOpen(true)} className="gap-2">
                <Plus className="w-4 h-4" />
                Add Document
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {filteredDocuments.map((doc) => (
            <DocumentCard 
              key={doc.doc_id} 
              document={doc} 
              onDelete={handleDelete}
              formatDate={formatDate}
              formatFileSize={formatFileSize}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface DocumentCardProps {
  document: DocumentResponse;
  onDelete: (id: string) => void;
  formatDate: (date: string) => string;
  formatFileSize: (bytes: number) => string;
}

function DocumentCard({ document, onDelete, formatDate, formatFileSize }: DocumentCardProps) {
  const fileMeta = document.file_meta as { original_name?: string; size?: number; type?: string } | null;

  return (
    <Card className="group hover:border-primary/50 transition-colors">
      <CardContent className="p-4">
        <div className="flex items-start justify-between mb-3">
          <div className="flex items-center gap-3">
            <div className="w-12 h-12 rounded-lg bg-muted flex items-center justify-center text-2xl">
              {documentTypeIcons[document.doc_type]}
            </div>
            <div className="min-w-0">
              <p className="font-medium capitalize">{document.doc_type}</p>
              <p className="text-sm text-muted-foreground truncate max-w-[150px]" title={fileMeta?.original_name}>
                {fileMeta?.original_name || 'Encrypted document'}
              </p>
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button 
                variant="ghost" 
                size="icon"
                className="opacity-0 group-hover:opacity-100 transition-opacity"
              >
                <MoreVertical className="w-4 h-4" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem disabled>
                <Download className="w-4 h-4 mr-2" />
                Download
              </DropdownMenuItem>
              <DropdownMenuItem 
                className="text-destructive"
                onClick={() => onDelete(document.doc_id)}
              >
                <Trash2 className="w-4 h-4 mr-2" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <div className="flex items-center justify-between text-sm">
          <span className="text-muted-foreground">
            {formatDate(document.created_at)}
          </span>
          <div className="flex items-center gap-2">
            {fileMeta?.size && (
              <span className="text-muted-foreground">
                {formatFileSize(fileMeta.size)}
              </span>
            )}
            {document.attestation_count > 0 && (
              <Badge variant="secondary" className="text-xs">
                {document.attestation_count} attestation{document.attestation_count !== 1 ? 's' : ''}
              </Badge>
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
