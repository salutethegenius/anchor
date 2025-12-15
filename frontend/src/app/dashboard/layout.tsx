'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Sidebar } from '@/components/anchor/sidebar';
import { useAccountStore } from '@/lib/store';
import { Loader2 } from 'lucide-react';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [hydrated, setHydrated] = useState(false);
  const { accountId } = useAccountStore();

  // Handle hydration
  useEffect(() => {
    setHydrated(true);
  }, []);

  // Redirect to login if not authenticated (after hydration)
  useEffect(() => {
    if (hydrated && !accountId) {
      router.push('/login');
    }
  }, [hydrated, accountId, router]);

  // Show loading while hydrating
  if (!hydrated) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Show nothing while redirecting
  if (!accountId) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <Loader2 className="w-8 h-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background">
      <Sidebar />
      <main className="flex-1 overflow-auto">
        <div className="container mx-auto p-6 max-w-6xl">
          {children}
        </div>
      </main>
    </div>
  );
}
