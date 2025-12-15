/**
 * Hydration hook for handling SSR/client state mismatches
 */

import { useEffect, useState } from 'react';

/**
 * Hook to detect when the component has been hydrated on the client
 * Useful for avoiding hydration mismatches with persisted stores
 */
export function useHydration() {
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  return hydrated;
}

/**
 * Hook to safely access a Zustand store that uses persist middleware
 * Returns the initial state on the server, and the persisted state on the client
 */
export function useHydratedStore<T, S>(
  store: (selector: (state: T) => S) => S,
  selector: (state: T) => S,
  initialState: S
): S {
  const [hydrated, setHydrated] = useState(false);
  const storeState = store(selector);

  useEffect(() => {
    setHydrated(true);
  }, []);

  return hydrated ? storeState : initialState;
}
