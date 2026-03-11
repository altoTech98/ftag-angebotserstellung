'use client';

import { useState, useRef, useCallback } from 'react';
import { Upload, FileText, CheckCircle2, AlertCircle, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { uploadCatalog } from '@/lib/actions/catalog-actions';

const ACCEPTED_EXTENSIONS = '.xlsx,.csv';
const ACCEPTED_TYPES = [
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'text/csv',
];

interface ValidationResult {
  total_rows: number;
  main_products: number;
  categories: number;
  errors: string[];
  warnings: string[];
}

interface CatalogUploadProps {
  canUpload: boolean;
  onUploadComplete?: () => void;
}

export function CatalogUpload({ canUpload, onUploadComplete }: CatalogUploadProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFileType = useCallback((file: File): boolean => {
    const ext = file.name.toLowerCase().split('.').pop();
    if (ext !== 'xlsx' && ext !== 'csv') {
      toast.error(`Dateityp nicht unterstuetzt: ${file.name}. Nur Excel (.xlsx) und CSV (.csv) erlaubt.`);
      return false;
    }
    return true;
  }, []);

  const handleUpload = useCallback(
    async (file: File) => {
      if (!validateFileType(file)) return;

      setIsUploading(true);
      setValidation(null);
      setUploadError(null);

      try {
        const formData = new FormData();
        formData.set('file', file);

        const result = await uploadCatalog(formData);

        if (result.error) {
          setUploadError(result.error);
          if (result.validation) {
            setValidation(result.validation as ValidationResult);
          }
          toast.error(result.error);
        } else if (result.success) {
          setValidation(result.validation as ValidationResult);
          toast.success('Katalog erfolgreich hochgeladen');
          onUploadComplete?.();
        }
      } catch (err) {
        const msg = err instanceof Error ? err.message : 'Fehler beim Hochladen';
        setUploadError(msg);
        toast.error(msg);
      } finally {
        setIsUploading(false);
      }
    },
    [validateFileType, onUploadComplete]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!isUploading && canUpload) setIsDragging(true);
    },
    [isUploading, canUpload]
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

      if (isUploading || !canUpload) return;

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        await handleUpload(files[0]);
      }
    },
    [isUploading, canUpload, handleUpload]
  );

  const handleFileSelect = useCallback(
    async (e: React.ChangeEvent<HTMLInputElement>) => {
      const files = Array.from(e.target.files || []);
      if (files.length > 0) {
        await handleUpload(files[0]);
      }
      if (fileInputRef.current) fileInputRef.current.value = '';
    },
    [handleUpload]
  );

  if (!canUpload) return null;

  return (
    <div className="space-y-4" data-testid="catalog-upload">
      {/* Dropzone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        data-testid="upload-dropzone"
        className={`relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          isDragging
            ? 'border-primary bg-primary/5'
            : 'border-border bg-muted/30 hover:border-muted-foreground/50'
        } ${isUploading ? 'pointer-events-none opacity-70' : ''}`}
      >
        {isUploading ? (
          <div className="flex flex-col items-center gap-3" data-testid="upload-progress">
            <FileText className="size-8 text-primary animate-pulse" />
            <p className="text-sm font-medium">Katalog wird hochgeladen und validiert...</p>
            <div className="h-2 w-full max-w-xs overflow-hidden rounded-full bg-muted">
              <div className="h-full w-full animate-pulse rounded-full bg-primary" />
            </div>
          </div>
        ) : (
          <>
            <Upload className="mb-3 size-8 text-muted-foreground" />
            <p className="mb-1 text-sm font-medium">
              Excel (.xlsx) oder CSV Datei hierher ziehen
            </p>
            <p className="mb-3 text-xs text-muted-foreground">
              oder klicken Sie auf den Button unten
            </p>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
              data-testid="upload-select-btn"
            >
              Datei auswaehlen
            </Button>
            <input
              ref={fileInputRef}
              type="file"
              accept={ACCEPTED_EXTENSIONS}
              className="hidden"
              onChange={handleFileSelect}
              data-testid="upload-file-input"
            />
          </>
        )}
      </div>

      {/* Validation results */}
      {validation && !uploadError && (
        <Card data-testid="validation-success">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-3">
              <CheckCircle2 className="size-5 text-green-600" />
              <span className="font-medium text-green-600">Validierung erfolgreich</span>
            </div>
            <div className="grid grid-cols-3 gap-4 text-sm">
              <div>
                <p className="text-muted-foreground">Produkte gesamt</p>
                <p className="font-semibold" data-testid="validation-total">{validation.total_rows}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Hauptprodukte</p>
                <p className="font-semibold" data-testid="validation-main">{validation.main_products}</p>
              </div>
              <div>
                <p className="text-muted-foreground">Kategorien</p>
                <p className="font-semibold" data-testid="validation-categories">{validation.categories}</p>
              </div>
            </div>
            {validation.warnings.length > 0 && (
              <div className="mt-3" data-testid="validation-warnings">
                <div className="flex items-center gap-1.5 text-sm text-yellow-600 mb-1">
                  <AlertTriangle className="size-4" />
                  <span className="font-medium">Warnungen</span>
                </div>
                <ul className="list-disc list-inside text-xs text-yellow-600 space-y-0.5">
                  {validation.warnings.map((w, i) => (
                    <li key={i}>{w}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Error display with validation details */}
      {uploadError && (
        <Card data-testid="validation-error">
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertCircle className="size-5 text-destructive" />
              <span className="font-medium text-destructive">{uploadError}</span>
            </div>
            {validation && validation.errors && validation.errors.length > 0 && (
              <ul className="list-disc list-inside text-xs text-destructive space-y-0.5" data-testid="validation-error-list">
                {validation.errors.map((e, i) => (
                  <li key={i}>{e}</li>
                ))}
              </ul>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
