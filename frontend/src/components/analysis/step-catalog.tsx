'use client';

import { useEffect } from 'react';
import { Database, Upload, Package, Calendar, CheckCircle2 } from 'lucide-react';
import Link from 'next/link';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

export interface CatalogInfo {
  id: string;
  name: string;
  productCount: number;
  updatedAt: Date | string;
  isActive: boolean;
}

interface StepCatalogProps {
  catalogId: string | null;
  onCatalogChange: (id: string) => void;
  catalogs: CatalogInfo[];
}

export function StepCatalog({ catalogId, onCatalogChange, catalogs }: StepCatalogProps) {
  // Auto-select if only one catalog exists
  useEffect(() => {
    if (!catalogId && catalogs.length === 1) {
      onCatalogChange(catalogs[0].id);
    }
  }, [catalogId, catalogs, onCatalogChange]);

  return (
    <div className="space-y-4">
      <h3 className="text-base font-medium">Produktkatalog auswaehlen</h3>
      <p className="text-sm text-muted-foreground">
        Der Katalog wird fuer die Zuordnung der Anforderungen zu Produkten
        verwendet.
      </p>

      {catalogs.length === 0 ? (
        <Card data-testid="no-catalogs">
          <CardContent className="flex flex-col items-center py-8 text-center">
            <Database className="mb-3 size-10 text-muted-foreground" />
            <p className="text-sm text-muted-foreground mb-3">
              Noch keine Kataloge vorhanden. Laden Sie zuerst einen Produktkatalog hoch.
            </p>
            <Link href="/katalog">
              <Button variant="outline" size="sm" className="gap-2" data-testid="upload-catalog-btn">
                <Upload className="size-4" />
                Katalog hochladen
              </Button>
            </Link>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {catalogs.map((catalog) => {
            const isSelected = catalogId === catalog.id;
            return (
              <Card
                key={catalog.id}
                data-testid="catalog-card"
                className={`cursor-pointer transition-all ${
                  isSelected
                    ? 'ring-2 ring-primary/50'
                    : 'ring-1 ring-foreground/10 hover:ring-foreground/20'
                }`}
                onClick={() => onCatalogChange(catalog.id)}
              >
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Database className="size-5 text-primary" />
                    {catalog.name}
                    {isSelected && (
                      <Badge variant="secondary" data-testid="catalog-selected-badge">
                        <CheckCircle2 className="size-3 mr-1" />
                        Ausgewaehlt
                      </Badge>
                    )}
                    {catalog.isActive && (
                      <Badge className="bg-green-100 text-green-700 border-green-200">
                        Aktiv
                      </Badge>
                    )}
                  </CardTitle>
                  <CardDescription>
                    Produktkatalog der Frank Tueren AG
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                    <span className="flex items-center gap-1.5">
                      <Package className="size-3.5" />
                      {catalog.productCount} Produkte
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Calendar className="size-3.5" />
                      {new Date(catalog.updatedAt).toLocaleDateString('de-CH')}
                    </span>
                  </div>
                </CardContent>
              </Card>
            );
          })}

          <Link href="/katalog">
            <Button
              variant="outline"
              className="gap-2"
              data-testid="upload-catalog-btn"
            >
              <Upload className="size-4" />
              Katalog hochladen
            </Button>
          </Link>
        </div>
      )}
    </div>
  );
}
