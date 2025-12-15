/**
 * ANCHOR State Management
 * Zustand store for client state
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { CitizenResponse, DocumentResponse } from './api/types';

interface AccountState {
  // Current account (null if not logged in)
  account: CitizenResponse | null;
  accountId: string | null;

  // Encryption keys (stored encrypted in localStorage)
  encryptedSecretKey: string | null;
  publicKey: string | null;

  // Actions
  setAccount: (account: CitizenResponse) => void;
  setKeys: (publicKey: string, encryptedSecretKey: string) => void;
  logout: () => void;
}

interface VaultState {
  // Cached documents
  documents: DocumentResponse[];
  isLoading: boolean;

  // Actions
  setDocuments: (documents: DocumentResponse[]) => void;
  addDocument: (document: DocumentResponse) => void;
  removeDocument: (docId: string) => void;
  setLoading: (loading: boolean) => void;
  clearVault: () => void;
}

interface UIState {
  // UI preferences
  sidebarOpen: boolean;
  theme: 'light' | 'dark' | 'system';

  // Actions
  toggleSidebar: () => void;
  setTheme: (theme: 'light' | 'dark' | 'system') => void;
}

/**
 * Account store - persisted to localStorage
 */
export const useAccountStore = create<AccountState>()(
  persist(
    (set) => ({
      account: null,
      accountId: null,
      encryptedSecretKey: null,
      publicKey: null,

      setAccount: (account) =>
        set({ account, accountId: account.account_id }),

      setKeys: (publicKey, encryptedSecretKey) =>
        set({ publicKey, encryptedSecretKey }),

      logout: () =>
        set({
          account: null,
          // Keep accountId, encryptedSecretKey, and publicKey for login
          // Only clear the account object
        }),
    }),
    {
      name: 'anchor-account',
      partialize: (state) => ({
        accountId: state.accountId,
        encryptedSecretKey: state.encryptedSecretKey,
        publicKey: state.publicKey,
      }),
    }
  )
);

/**
 * Vault store - not persisted (documents fetched from API)
 */
export const useVaultStore = create<VaultState>((set) => ({
  documents: [],
  isLoading: false,

  setDocuments: (documents) => set({ documents }),

  addDocument: (document) =>
    set((state) => ({
      documents: [document, ...state.documents],
    })),

  removeDocument: (docId) =>
    set((state) => ({
      documents: state.documents.filter((d) => d.doc_id !== docId),
    })),

  setLoading: (isLoading) => set({ isLoading }),

  clearVault: () => set({ documents: [], isLoading: false }),
}));

/**
 * UI store - persisted preferences
 */
export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
      sidebarOpen: true,
      theme: 'system',

      toggleSidebar: () =>
        set((state) => ({ sidebarOpen: !state.sidebarOpen })),

      setTheme: (theme) => set({ theme }),
    }),
    {
      name: 'anchor-ui',
    }
  )
);
