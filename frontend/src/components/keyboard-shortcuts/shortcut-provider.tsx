'use client';

import { useState, useEffect } from 'react';
import { useKeyboardShortcuts } from '@/lib/hooks/use-keyboard-shortcuts';
import { ShortcutsHelp } from './shortcuts-help';

interface ShortcutProviderProps {
  children: React.ReactNode;
}

export function ShortcutProvider({ children }: ShortcutProviderProps) {
  const [helpOpen, setHelpOpen] = useState(false);

  useKeyboardShortcuts();

  useEffect(() => {
    function handleToggle() {
      setHelpOpen((prev) => !prev);
    }

    window.addEventListener('toggle-shortcuts-help', handleToggle);
    return () =>
      window.removeEventListener('toggle-shortcuts-help', handleToggle);
  }, []);

  return (
    <>
      {children}
      <ShortcutsHelp open={helpOpen} onOpenChange={setHelpOpen} />
    </>
  );
}
