'use client';

import { useState, useEffect, useTransition } from 'react';
import { toast } from 'sonner';
import { X } from 'lucide-react';
import {
  shareProject,
  removeShare,
  getProjectShares,
} from '@/lib/actions/project-actions';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

interface ShareData {
  id: string;
  projectId: string;
  userId: string;
  role: string;
  user: { id: string; name: string; email: string };
}

interface ShareDialogProps {
  projectId: string;
  projectName: string;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ShareDialog({
  projectId,
  projectName,
  open,
  onOpenChange,
}: ShareDialogProps) {
  const [shares, setShares] = useState<ShareData[]>([]);
  const [email, setEmail] = useState('');
  const [role, setRole] = useState('viewer');
  const [isSharing, startSharing] = useTransition();
  const [removingId, setRemovingId] = useState<string | null>(null);

  useEffect(() => {
    if (open) {
      loadShares();
    }
  }, [open]);

  async function loadShares() {
    try {
      const data = await getProjectShares(projectId);
      setShares(data as ShareData[]);
    } catch {
      toast.error('Freigaben konnten nicht geladen werden');
    }
  }

  function handleShare() {
    if (!email.trim()) return;

    startSharing(async () => {
      try {
        const result = await shareProject(projectId, email.trim(), role);
        if ('error' in result) {
          toast.error(result.error);
          return;
        }
        toast.success(`Projekt mit ${email} geteilt`);
        setEmail('');
        await loadShares();
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : 'Teilen fehlgeschlagen'
        );
      }
    });
  }

  async function handleRemove(shareId: string) {
    setRemovingId(shareId);
    try {
      await removeShare(shareId);
      toast.success('Freigabe entfernt');
      await loadShares();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : 'Entfernen fehlgeschlagen'
      );
    } finally {
      setRemovingId(null);
    }
  }

  const roleBadgeClass: Record<string, string> = {
    viewer:
      'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    editor:
      'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Projekt teilen</DialogTitle>
          <DialogDescription>
            Teilen Sie &quot;{projectName}&quot; mit anderen Benutzern.
          </DialogDescription>
        </DialogHeader>

        {/* Share form */}
        <div className="space-y-3">
          <div className="space-y-1.5">
            <Label htmlFor="share-email">E-Mail</Label>
            <Input
              id="share-email"
              type="email"
              placeholder="benutzer@ftag.ch"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault();
                  handleShare();
                }
              }}
            />
          </div>
          <div className="flex items-end gap-2">
            <div className="flex-1 space-y-1.5">
              <Label htmlFor="share-role">Rolle</Label>
              <select
                id="share-role"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={role}
                onChange={(e) => setRole(e.target.value)}
              >
                <option value="viewer">Betrachter</option>
                <option value="editor">Bearbeiter</option>
              </select>
            </div>
            <Button onClick={handleShare} disabled={isSharing || !email.trim()}>
              {isSharing ? 'Wird geteilt...' : 'Teilen'}
            </Button>
          </div>
        </div>

        {/* Current shares */}
        {shares.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-sm font-medium">Aktuelle Freigaben</h4>
            <ul className="divide-y divide-border rounded-lg border border-border">
              {shares.map((share) => (
                <li
                  key={share.id}
                  className="flex items-center justify-between px-3 py-2"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">
                      {share.user.name}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {share.user.email}
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span
                      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${roleBadgeClass[share.role] || roleBadgeClass.viewer}`}
                    >
                      {share.role === 'editor' ? 'Bearbeiter' : 'Betrachter'}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      className="size-7 p-0"
                      onClick={() => handleRemove(share.id)}
                      disabled={removingId === share.id}
                      aria-label={`Freigabe fuer ${share.user.name} entfernen`}
                    >
                      <X className="size-4" />
                    </Button>
                  </div>
                </li>
              ))}
            </ul>
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}
