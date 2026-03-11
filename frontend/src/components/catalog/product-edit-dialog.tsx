'use client';

import { useState } from 'react';
import { Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { saveProductOverride } from '@/lib/actions/catalog-actions';

interface ProductData {
  row_index: number;
  category: string;
  summary: string;
  fields: Record<string, unknown>;
  kostentraeger?: string;
  hasOverride: boolean;
  overrideAction: string | null;
  overrideId: string | null;
}

interface ProductEditDialogProps {
  catalogId: string;
  product?: ProductData;
  mode: 'add' | 'edit';
  onClose: () => void;
}

const FORM_FIELDS = [
  { key: 'kategorie', label: 'Kategorie', required: true },
  { key: 'kostentraeger', label: 'Kostentraeger', required: true },
  { key: 'tuertyp', label: 'Tuertyp', required: false },
  { key: 'tuerblattausfuehrung', label: 'Tuerblattausfuehrung', required: false },
  { key: 'anzahl_fluegel', label: 'Anzahl Fluegel', required: false },
  { key: 'brandschutzklasse', label: 'Brandschutzklasse', required: false },
  { key: 'lichtmass_max', label: 'Lichtmass max', required: false },
  { key: 'schallschutz_db', label: 'Schallschutz (dB)', required: false },
  { key: 'widerstandsklasse', label: 'Widerstandsklasse', required: false },
  { key: 'glasausschnitt', label: 'Glasausschnitt', required: false },
  { key: 'oberflaeche', label: 'Oberflaeche', required: false },
] as const;

export function ProductEditDialog({
  catalogId,
  product,
  mode,
  onClose,
}: ProductEditDialogProps) {
  const fields = product?.fields ?? {};
  const [formData, setFormData] = useState<Record<string, string>>(() => {
    const initial: Record<string, string> = {};
    for (const f of FORM_FIELDS) {
      if (f.key === 'kategorie') {
        initial[f.key] = product?.category ?? '';
      } else if (f.key === 'kostentraeger') {
        initial[f.key] = product?.kostentraeger ?? '';
      } else {
        initial[f.key] = String(fields[f.key] ?? '');
      }
    }
    return initial;
  });
  const [isSaving, setIsSaving] = useState(false);

  const handleChange = (key: string, value: string) => {
    setFormData((prev) => ({ ...prev, [key]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Validate required fields
    const missing = FORM_FIELDS.filter(
      (f) => f.required && !formData[f.key]?.trim()
    );
    if (missing.length > 0) {
      toast.error(
        `Pflichtfelder fehlen: ${missing.map((f) => f.label).join(', ')}`
      );
      return;
    }

    setIsSaving(true);
    try {
      const productKey =
        formData.kostentraeger || product?.kostentraeger || String(product?.row_index ?? 'new');

      await saveProductOverride(catalogId, productKey, mode, formData);

      toast.success(
        mode === 'add'
          ? 'Produkt hinzugefuegt'
          : 'Produkt aktualisiert'
      );
      onClose();
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : 'Fehler beim Speichern'
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <Dialog
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <DialogContent className="sm:max-w-lg max-h-[85vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle data-testid="dialog-title">
            {mode === 'add' ? 'Neues Produkt hinzufuegen' : 'Produkt bearbeiten'}
          </DialogTitle>
          <DialogDescription>
            {mode === 'add'
              ? 'Geben Sie die Produktdaten ein.'
              : `Bearbeiten Sie die Felder fuer "${product?.kostentraeger || product?.row_index}".`}
          </DialogDescription>
        </DialogHeader>

        <form onSubmit={handleSubmit} data-testid="product-edit-form">
          <div className="grid gap-3 py-4">
            {FORM_FIELDS.map((field) => (
              <div key={field.key} className="grid grid-cols-3 items-center gap-3">
                <Label htmlFor={field.key} className="text-right text-sm">
                  {field.label}
                  {field.required && (
                    <span className="text-destructive ml-0.5">*</span>
                  )}
                </Label>
                <Input
                  id={field.key}
                  value={formData[field.key] ?? ''}
                  onChange={(e) => handleChange(field.key, e.target.value)}
                  className="col-span-2"
                  data-testid={`field-${field.key}`}
                />
              </div>
            ))}
          </div>

          <DialogFooter>
            <Button
              type="button"
              variant="outline"
              onClick={onClose}
              disabled={isSaving}
            >
              Abbrechen
            </Button>
            <Button type="submit" disabled={isSaving} data-testid="save-btn">
              {isSaving ? (
                <>
                  <Loader2 className="size-4 animate-spin mr-1" />
                  Speichern...
                </>
              ) : (
                'Speichern'
              )}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
