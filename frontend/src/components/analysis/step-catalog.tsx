'use client';

import { useEffect } from 'react';
import { Database, Upload, Info } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const DEFAULT_CATALOG_ID = 'ftag-default';

interface StepCatalogProps {
  catalogId: string | null;
  onCatalogChange: (id: string) => void;
}

export function StepCatalog({ catalogId, onCatalogChange }: StepCatalogProps) {
  // Auto-select default catalog on mount
  useEffect(() => {
    if (!catalogId) {
      onCatalogChange(DEFAULT_CATALOG_ID);
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const isDefault = catalogId === DEFAULT_CATALOG_ID;

  return (
    <div className="space-y-4">
      <h3 className="text-base font-medium">Produktkatalog auswaehlen</h3>
      <p className="text-sm text-muted-foreground">
        Der Katalog wird fuer die Zuordnung der Anforderungen zu Produkten
        verwendet.
      </p>

      <Card
        data-testid="catalog-card"
        className={
          isDefault
            ? 'ring-2 ring-primary/50'
            : 'ring-1 ring-foreground/10'
        }
      >
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="size-5 text-primary" />
            FTAG Produktuebersicht
            {isDefault && (
              <Badge variant="secondary" data-testid="catalog-selected-badge">
                Ausgewaehlt
              </Badge>
            )}
          </CardTitle>
          <CardDescription>
            Standard-Produktkatalog der Frank Tueren AG
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
            <span>~891 Produkte</span>
            <span>Letzte Aktualisierung: Standard</span>
          </div>
        </CardContent>
      </Card>

      <div className="relative">
        <Button
          variant="outline"
          disabled
          className="gap-2"
          data-testid="upload-catalog-btn"
        >
          <Upload className="size-4" />
          Katalog hochladen
        </Button>
        <div className="mt-1.5 flex items-center gap-1.5 text-xs text-muted-foreground">
          <Info className="size-3.5" />
          <span>Verfuegbar in Phase 14</span>
        </div>
      </div>
    </div>
  );
}
