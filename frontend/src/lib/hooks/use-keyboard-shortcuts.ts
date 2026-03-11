'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';

const SHORTCUT_MAP: Record<string, string> = {
  n: '/neue-analyse',
  d: '/dashboard',
  p: '/projekte',
  k: '/katalog',
};

export function useKeyboardShortcuts() {
  const router = useRouter();

  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      // Skip when typing in inputs
      const target = e.target as HTMLElement;
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return;
      }

      // Skip when modifier keys are pressed (except shift for ?)
      if (e.ctrlKey || e.metaKey || e.altKey) {
        return;
      }

      // ? key (shift + / on most keyboards)
      if (e.key === '?') {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent('toggle-shortcuts-help'));
        return;
      }

      // Navigation shortcuts
      const route = SHORTCUT_MAP[e.key];
      if (route) {
        e.preventDefault();
        router.push(route);
      }
    }

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [router]);
}
