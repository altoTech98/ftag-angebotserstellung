'use client';

import { useTransition } from 'react';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { archiveProject, deleteProject } from '@/lib/actions/project-actions';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';

export const ARCHIVE_WARNING =
  'Projekt wird archiviert und erscheint nicht mehr in der aktiven Liste.';

export const DELETE_WARNING =
  'Projekt und alle zugehoerigen Dateien werden unwiderruflich geloescht.';

interface ArchiveDialogProps {
  projectId: string;
  projectName: string;
  action: 'archive' | 'delete';
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function ArchiveDialog({
  projectId,
  projectName,
  action,
  open,
  onOpenChange,
}: ArchiveDialogProps) {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const isDelete = action === 'delete';
  const title = isDelete ? 'Projekt loeschen' : 'Projekt archivieren';
  const warning = isDelete ? DELETE_WARNING : ARCHIVE_WARNING;
  const confirmLabel = isDelete ? 'Unwiderruflich loeschen' : 'Archivieren';

  function handleConfirm() {
    startTransition(async () => {
      try {
        if (isDelete) {
          await deleteProject(projectId);
          toast.success(`Projekt "${projectName}" geloescht`);
        } else {
          await archiveProject(projectId);
          toast.success(`Projekt "${projectName}" archiviert`);
        }
        onOpenChange(false);
        router.push('/projekte');
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : 'Aktion fehlgeschlagen'
        );
      }
    });
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            <strong>{projectName}</strong>: {warning}
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose>
            <Button variant="outline" disabled={isPending}>
              Abbrechen
            </Button>
          </DialogClose>
          <Button
            variant={isDelete ? 'destructive' : 'default'}
            onClick={handleConfirm}
            disabled={isPending}
          >
            {isPending ? 'Bitte warten...' : confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
