'use client';

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';

interface ShortcutsHelpProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

const SHORTCUTS = [
  { key: 'N', description: 'Neue Analyse starten' },
  { key: 'D', description: 'Dashboard' },
  { key: 'P', description: 'Projekte' },
  { key: 'K', description: 'Katalog' },
  { key: '?', description: 'Diese Hilfe anzeigen' },
];

export function ShortcutsHelp({ open, onOpenChange }: ShortcutsHelpProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Tastenkuerzel</DialogTitle>
          <DialogDescription>
            Navigieren Sie schnell mit der Tastatur.
          </DialogDescription>
        </DialogHeader>
        <div className="space-y-2">
          {SHORTCUTS.map((shortcut) => (
            <div
              key={shortcut.key}
              className="flex items-center justify-between py-1"
            >
              <span className="text-sm text-muted-foreground">
                {shortcut.description}
              </span>
              <kbd className="inline-flex items-center justify-center rounded bg-muted px-2 py-1 font-mono text-sm">
                {shortcut.key}
              </kbd>
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}
