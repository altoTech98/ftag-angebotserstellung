'use client';

import { useState, useRef, useCallback } from 'react';
import { upload } from '@vercel/blob/client';
import { Upload, FileText, AlertCircle } from 'lucide-react';
import { toast } from 'sonner';
import { saveFileMetadata } from '@/lib/actions/file-actions';
import { Button } from '@/components/ui/button';

export const ACCEPTED_TYPES = [
  'application/pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
];

const ACCEPTED_EXTENSIONS = '.pdf,.docx,.xlsx';

interface FileDropzoneProps {
  projectId: string;
  onFileUploaded?: () => void;
}

export function FileDropzone({ projectId, onFileUploaded }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = useCallback((file: File): boolean => {
    if (!ACCEPTED_TYPES.includes(file.type)) {
      toast.error(`Dateityp nicht unterstuetzt: ${file.name}. Nur PDF, DOCX und XLSX erlaubt.`);
      return false;
    }
    return true;
  }, []);

  const uploadFile = useCallback(
    async (file: File) => {
      if (!validateFile(file)) return;

      setIsUploading(true);
      setProgress(0);

      try {
        const blob = await upload(file.name, file, {
          access: 'private',
          handleUploadUrl: '/api/upload',
          multipart: true,
          onUploadProgress: ({ percentage }) => {
            setProgress(percentage);
          },
        });

        await saveFileMetadata({
          name: file.name,
          blobUrl: blob.url,
          downloadUrl: blob.downloadUrl,
          size: file.size,
          contentType: file.type,
          projectId,
        });

        toast.success(`${file.name} erfolgreich hochgeladen`);
        onFileUploaded?.();
      } catch (err) {
        toast.error(
          err instanceof Error
            ? err.message
            : 'Fehler beim Hochladen der Datei'
        );
      } finally {
        setIsUploading(false);
        setProgress(0);
      }
    },
    [projectId, onFileUploaded, validateFile]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!isUploading) setIsDragging(true);
    },
    [isUploading]
  );

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (isUploading) return;

      const files = Array.from(e.dataTransfer.files);
      for (const file of files) {
        await uploadFile(file);
      }
    },
    [isUploading, uploadFile]
  );

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      for (const file of files) {
        await uploadFile(file);
      }
      // Reset the input so the same file can be selected again
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
    [uploadFile]
  );

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
        isDragging
          ? 'border-primary bg-primary/5'
          : 'border-border bg-muted/30 hover:border-muted-foreground/50'
      } ${isUploading ? 'pointer-events-none opacity-70' : ''}`}
    >
      {isUploading ? (
        <div className="flex w-full flex-col items-center gap-3">
          <FileText className="size-8 text-primary" />
          <p className="text-sm font-medium">Wird hochgeladen...</p>
          <div className="h-2 w-full max-w-xs overflow-hidden rounded-full bg-muted">
            <div
              className="h-full rounded-full bg-primary transition-all duration-200"
              style={{ width: `${progress}%` }}
            />
          </div>
          <p className="text-xs text-muted-foreground">{Math.round(progress)}%</p>
        </div>
      ) : (
        <>
          <Upload className="mb-3 size-8 text-muted-foreground" />
          <p className="mb-1 text-sm font-medium">
            PDF, DOCX oder XLSX hierher ziehen
          </p>
          <p className="mb-3 text-xs text-muted-foreground">
            oder klicken Sie auf den Button unten
          </p>
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => fileInputRef.current?.click()}
          >
            Dateien auswaehlen
          </Button>
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_EXTENSIONS}
            multiple
            className="hidden"
            onChange={handleFileSelect}
          />
        </>
      )}
    </div>
  );
}
