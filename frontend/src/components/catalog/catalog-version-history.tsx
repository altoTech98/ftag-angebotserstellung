'use client';

import { useState, useTransition } from 'react';
import {
  CheckCircle2,
  ArrowRightLeft,
  RotateCcw,
  Loader2,
  Calendar,
  Package,
  Layers,
  FolderTree,
} from 'lucide-react';
import { toast } from 'sonner';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { rollbackVersion, compareVersions } from '@/lib/actions/catalog-actions';

interface CatalogVersion {
  id: string;
  versionNum: number;
  fileName: string;
  totalProducts: number;
  mainProducts: number;
  categories: number;
  uploadedBy: string;
  isActive: boolean;
  notes: string | null;
  createdAt: string | Date;
}

interface DiffResult {
  old_count: number;
  new_count: number;
  added: number;
  removed: number;
  error?: string;
}

interface CatalogVersionHistoryProps {
  catalogId: string;
  versions: CatalogVersion[];
  canManage: boolean;
}

export function CatalogVersionHistory({
  catalogId,
  versions,
  canManage,
}: CatalogVersionHistoryProps) {
  const [isPending, startTransition] = useTransition();
  const [rollbackTarget, setRollbackTarget] = useState<string | null>(null);
  const [compareA, setCompareA] = useState<string>('');
  const [compareB, setCompareB] = useState<string>('');
  const [diffResult, setDiffResult] = useState<DiffResult | null>(null);
  const [isComparing, setIsComparing] = useState(false);

  const handleRollback = (versionId: string, versionNum: number) => {
    if (
      !confirm(
        `Version ${versionNum} aktivieren? Der aktuelle Katalog wird ersetzt.`
      )
    )
      return;

    setRollbackTarget(versionId);
    startTransition(async () => {
      try {
        const result = await rollbackVersion(catalogId, versionId);
        if (result && 'error' in result) {
          toast.error(result.error as string);
        } else {
          toast.success(`Version ${versionNum} aktiviert`);
        }
      } catch (err) {
        toast.error(
          err instanceof Error ? err.message : 'Fehler beim Aktivieren'
        );
      } finally {
        setRollbackTarget(null);
      }
    });
  };

  const handleCompare = async () => {
    if (!compareA || !compareB) {
      toast.error('Bitte waehlen Sie zwei Versionen aus');
      return;
    }
    if (compareA === compareB) {
      toast.error('Bitte waehlen Sie zwei verschiedene Versionen');
      return;
    }

    setIsComparing(true);
    setDiffResult(null);
    try {
      const result = await compareVersions(compareA, compareB);
      if ('error' in result) {
        toast.error(result.error as string);
      } else {
        setDiffResult(result as DiffResult);
      }
    } catch (err) {
      toast.error(
        err instanceof Error ? err.message : 'Vergleich fehlgeschlagen'
      );
    } finally {
      setIsComparing(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="version-history">
      {/* Comparison section */}
      {versions.length >= 2 && (
        <Card data-testid="version-compare">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <ArrowRightLeft className="size-4" />
              Versionen vergleichen
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Version A</p>
                <Select
                  value={compareA}
                  onValueChange={(val: string | null) =>
                    setCompareA(val ?? '')
                  }
                >
                  <SelectTrigger data-testid="compare-a">
                    <SelectValue placeholder="Version waehlen" />
                  </SelectTrigger>
                  <SelectContent>
                    {versions.map((v) => (
                      <SelectItem key={v.id} value={v.id}>
                        Version {v.versionNum}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <p className="text-xs text-muted-foreground mb-1">Version B</p>
                <Select
                  value={compareB}
                  onValueChange={(val: string | null) =>
                    setCompareB(val ?? '')
                  }
                >
                  <SelectTrigger data-testid="compare-b">
                    <SelectValue placeholder="Version waehlen" />
                  </SelectTrigger>
                  <SelectContent>
                    {versions.map((v) => (
                      <SelectItem key={v.id} value={v.id}>
                        Version {v.versionNum}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <Button
                size="sm"
                onClick={handleCompare}
                disabled={isComparing || !compareA || !compareB}
                data-testid="compare-btn"
              >
                {isComparing ? (
                  <Loader2 className="size-4 animate-spin" />
                ) : (
                  'Vergleichen'
                )}
              </Button>
            </div>

            {diffResult && (
              <div
                className="grid grid-cols-2 gap-4 rounded-md border bg-muted/30 p-4 text-sm sm:grid-cols-4"
                data-testid="diff-result"
              >
                <div>
                  <p className="text-muted-foreground">Version A</p>
                  <p className="font-semibold">{diffResult.old_count} Produkte</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Version B</p>
                  <p className="font-semibold">{diffResult.new_count} Produkte</p>
                </div>
                <div>
                  <p className="text-muted-foreground">Hinzugefuegt</p>
                  <p className="font-semibold text-green-600">
                    +{diffResult.added}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground">Entfernt</p>
                  <p className="font-semibold text-destructive">
                    -{diffResult.removed}
                  </p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Version list */}
      <div className="space-y-3" data-testid="version-list">
        {versions.map((version) => (
          <Card
            key={version.id}
            data-testid={`version-${version.versionNum}`}
            className={version.isActive ? 'ring-2 ring-green-500/30' : ''}
          >
            <CardContent className="flex items-center justify-between pt-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <span className="font-medium">
                    Version {version.versionNum}
                  </span>
                  {version.isActive && (
                    <Badge
                      className="bg-green-100 text-green-700 border-green-200"
                      data-testid={`active-badge-${version.versionNum}`}
                    >
                      <CheckCircle2 className="size-3 mr-1" />
                      Aktiv
                    </Badge>
                  )}
                </div>
                <div className="flex flex-wrap gap-3 text-sm text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <Calendar className="size-3" />
                    {new Date(version.createdAt).toLocaleDateString('de-CH')}
                  </span>
                  <span className="flex items-center gap-1">
                    <Package className="size-3" />
                    {version.totalProducts} Produkte
                  </span>
                  <span className="flex items-center gap-1">
                    <Layers className="size-3" />
                    {version.mainProducts} Hauptprodukte
                  </span>
                  <span className="flex items-center gap-1">
                    <FolderTree className="size-3" />
                    {version.categories} Kategorien
                  </span>
                  <span>{version.fileName}</span>
                </div>
                {version.notes && (
                  <p className="text-xs text-muted-foreground italic">
                    {version.notes}
                  </p>
                )}
              </div>

              {canManage && !version.isActive && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() =>
                    handleRollback(version.id, version.versionNum)
                  }
                  disabled={isPending && rollbackTarget === version.id}
                  data-testid={`rollback-btn-${version.versionNum}`}
                >
                  {isPending && rollbackTarget === version.id ? (
                    <Loader2 className="size-3.5 animate-spin mr-1" />
                  ) : (
                    <RotateCcw className="size-3.5 mr-1" />
                  )}
                  Aktivieren
                </Button>
              )}
            </CardContent>
          </Card>
        ))}
      </div>

      {versions.length === 0 && (
        <div className="rounded-lg border border-border bg-muted/30 p-8 text-center text-muted-foreground">
          Noch keine Versionen vorhanden.
        </div>
      )}
    </div>
  );
}
