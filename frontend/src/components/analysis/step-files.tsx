'use client';

import { useEffect } from 'react';
import { FileText, FileSpreadsheet, File } from 'lucide-react';
import { Checkbox } from '@/components/ui/checkbox';
import type { ProjectFile } from './types';

interface StepFilesProps {
  files: ProjectFile[];
  selectedIds: string[];
  onSelectionChange: (ids: string[]) => void;
}

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(contentType: string) {
  if (contentType.includes('pdf')) return FileText;
  if (
    contentType.includes('spreadsheet') ||
    contentType.includes('excel') ||
    contentType.includes('xlsx')
  )
    return FileSpreadsheet;
  return File;
}

export function StepFiles({
  files,
  selectedIds,
  onSelectionChange,
}: StepFilesProps) {
  // Pre-select all files on first mount (when no files are selected yet)
  useEffect(() => {
    if (selectedIds.length === 0 && files.length > 0) {
      onSelectionChange(files.map((f) => f.id));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  function toggleFile(fileId: string) {
    if (selectedIds.includes(fileId)) {
      onSelectionChange(selectedIds.filter((id) => id !== fileId));
    } else {
      onSelectionChange([...selectedIds, fileId]);
    }
  }

  function toggleAll() {
    if (selectedIds.length === files.length) {
      onSelectionChange([]);
    } else {
      onSelectionChange(files.map((f) => f.id));
    }
  }

  if (files.length === 0) {
    return (
      <div className="flex flex-col items-center rounded-lg border border-dashed border-border bg-muted/30 py-8 text-center">
        <File className="mb-3 size-8 text-muted-foreground" />
        <p className="text-sm text-muted-foreground">
          Keine Dateien vorhanden
        </p>
        <p className="text-xs text-muted-foreground">
          Laden Sie zuerst Dateien in der Projektansicht hoch.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h3 className="text-base font-medium">
          Dateien fuer die Analyse auswaehlen
        </h3>
        <button
          type="button"
          onClick={toggleAll}
          className="text-sm text-primary hover:underline"
        >
          {selectedIds.length === files.length
            ? 'Keine auswaehlen'
            : 'Alle auswaehlen'}
        </button>
      </div>

      <p className="text-sm text-muted-foreground">
        {selectedIds.length} von {files.length} Datei
        {files.length !== 1 ? 'en' : ''} ausgewaehlt
      </p>

      <ul className="divide-y divide-border rounded-lg border border-border">
        {files.map((file) => {
          const Icon = getFileIcon(file.contentType);
          const isSelected = selectedIds.includes(file.id);

          return (
            <li key={file.id}>
              <label className="flex cursor-pointer items-center gap-3 px-4 py-3 hover:bg-muted/50 transition-colors">
                <Checkbox
                  checked={isSelected}
                  onCheckedChange={() => toggleFile(file.id)}
                  aria-label={`Datei ${file.name} auswaehlen`}
                />
                <Icon className="size-5 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium">{file.name}</p>
                </div>
                <span className="shrink-0 text-xs text-muted-foreground">
                  {formatFileSize(file.size)}
                </span>
              </label>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
