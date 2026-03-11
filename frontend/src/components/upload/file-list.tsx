'use client';

import { useState } from 'react';
import { FileText, Trash2 } from 'lucide-react';
import { toast } from 'sonner';
import { deleteFile } from '@/lib/actions/file-actions';
import { Button } from '@/components/ui/button';

export interface FileData {
  id: string;
  name: string;
  size: number;
  contentType: string;
  downloadUrl: string;
  createdAt: Date | string;
}

interface FileListProps {
  files: FileData[];
  onFileDeleted?: () => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function contentTypeBadge(contentType: string) {
  const labels: Record<string, string> = {
    'application/pdf': 'PDF',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'DOCX',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'XLSX',
  };
  return (
    <span className="inline-flex items-center rounded-full bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
      {labels[contentType] || contentType}
    </span>
  );
}

export function FileList({ files, onFileDeleted }: FileListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  async function handleDelete(fileId: string, fileName: string) {
    setDeletingId(fileId);
    try {
      await deleteFile(fileId);
      toast.success(`${fileName} geloescht`);
      onFileDeleted?.();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : 'Fehler beim Loeschen der Datei'
      );
    } finally {
      setDeletingId(null);
    }
  }

  if (files.length === 0) {
    return (
      <p className="py-4 text-center text-sm text-muted-foreground">
        Noch keine Dateien hochgeladen
      </p>
    );
  }

  return (
    <ul className="divide-y divide-border rounded-lg border border-border">
      {files.map((file) => (
        <li
          key={file.id}
          className="flex items-center justify-between gap-3 px-4 py-3"
        >
          <div className="flex items-center gap-3 overflow-hidden">
            <FileText className="size-5 shrink-0 text-muted-foreground" />
            <div className="min-w-0">
              <p className="truncate text-sm font-medium">{file.name}</p>
              <div className="flex items-center gap-2 text-xs text-muted-foreground">
                <span>{formatFileSize(file.size)}</span>
                {contentTypeBadge(file.contentType)}
              </div>
            </div>
          </div>
          <Button
            variant="ghost"
            size="icon-xs"
            onClick={() => handleDelete(file.id, file.name)}
            disabled={deletingId === file.id}
            aria-label={`${file.name} loeschen`}
          >
            <Trash2 className="size-4 text-muted-foreground hover:text-destructive" />
          </Button>
        </li>
      ))}
    </ul>
  );
}
