'use client';

import React, { useState, useMemo, useCallback } from 'react';
import { ArrowUpDown, Download, Loader2, Search } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { ConfidenceBadge } from '@/components/analysis/confidence-badge';
import { ResultDetail } from '@/components/analysis/result-detail';
import { getConfidenceLevel } from '@/components/analysis/types';
import type { AnalysisResult, MatchEntry, WizardState } from '@/components/analysis/types';

interface StepResultsProps {
  result: AnalysisResult;
  config: WizardState['config'];
  onExpandRow: (index: number) => void;
  expandedRow: number | null;
}

type SortField = 'nr' | 'beschreibung' | 'position' | 'produkt' | 'artikelnr' | 'konfidenz';
type SortDir = 'asc' | 'desc';

interface FlatEntry extends MatchEntry {
  nr: number;
}

function truncate(str: string, max: number): string {
  if (str.length <= max) return str;
  return str.slice(0, max) + '...';
}

export function StepResults({ result, config, onExpandRow, expandedRow }: StepResultsProps) {
  const [searchQuery, setSearchQuery] = useState('');
  const [confidenceFilter, setConfidenceFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('nr');
  const [sortDir, setSortDir] = useState<SortDir>('asc');
  const [isDownloading, setIsDownloading] = useState(false);

  // Flatten all entries into a single numbered list
  const allEntries: FlatEntry[] = useMemo(() => {
    const combined = [
      ...result.matched,
      ...result.partial,
      ...result.unmatched,
    ];
    return combined.map((entry, idx) => ({ ...entry, nr: idx + 1 }));
  }, [result]);

  // Compute filter summary counts
  const filterCounts = useMemo(() => {
    let high = 0;
    let medium = 0;
    let low = 0;
    let gap = 0;
    for (const entry of allEntries) {
      if (entry.confidence === 0 || entry.status === 'unmatched') {
        gap++;
      } else {
        const level = getConfidenceLevel(entry.confidence, config.highThreshold, config.lowThreshold);
        if (level === 'high') high++;
        else if (level === 'medium') medium++;
        else low++;
      }
    }
    return { high, medium, low, gap };
  }, [allEntries, config]);

  // Filter entries
  const filteredEntries = useMemo(() => {
    let entries = allEntries;

    // Text search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      entries = entries.filter(
        (e) =>
          e.beschreibung.toLowerCase().includes(q) ||
          e.position.toLowerCase().includes(q) ||
          e.reason.toLowerCase().includes(q)
      );
    }

    // Confidence filter
    if (confidenceFilter !== 'all') {
      entries = entries.filter((e) => {
        if (confidenceFilter === 'gap') {
          return e.confidence === 0 || e.status === 'unmatched';
        }
        if (e.confidence === 0 || e.status === 'unmatched') return false;
        const level = getConfidenceLevel(e.confidence, config.highThreshold, config.lowThreshold);
        return level === confidenceFilter;
      });
    }

    return entries;
  }, [allEntries, searchQuery, confidenceFilter, config]);

  // Sort entries
  const sortedEntries = useMemo(() => {
    const sorted = [...filteredEntries];
    sorted.sort((a, b) => {
      let cmp = 0;
      switch (sortField) {
        case 'nr':
          cmp = a.nr - b.nr;
          break;
        case 'beschreibung':
          cmp = a.beschreibung.localeCompare(b.beschreibung, 'de');
          break;
        case 'position':
          cmp = a.position.localeCompare(b.position, 'de');
          break;
        case 'produkt': {
          const ap = a.matched_products[0]?.bezeichnung || '';
          const bp = b.matched_products[0]?.bezeichnung || '';
          cmp = ap.localeCompare(bp, 'de');
          break;
        }
        case 'artikelnr': {
          const aa = a.matched_products[0]?.artikelnr || '';
          const ba = b.matched_products[0]?.artikelnr || '';
          cmp = aa.localeCompare(ba, 'de');
          break;
        }
        case 'konfidenz':
          cmp = a.confidence - b.confidence;
          break;
      }
      return sortDir === 'asc' ? cmp : -cmp;
    });
    return sorted;
  }, [filteredEntries, sortField, sortDir]);

  // Toggle sort
  const handleSort = useCallback(
    (field: SortField) => {
      if (sortField === field) {
        setSortDir((d) => (d === 'asc' ? 'desc' : 'asc'));
      } else {
        setSortField(field);
        setSortDir('asc');
      }
    },
    [sortField]
  );

  // Excel download
  const handleDownloadExcel = useCallback(async () => {
    setIsDownloading(true);
    try {
      // 1. Trigger generation
      const genResponse = await fetch('/api/backend/result/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          requirements: result,
          matching: result,
        }),
      });
      if (!genResponse.ok) {
        throw new Error('Excel-Generierung fehlgeschlagen');
      }
      const { job_id } = await genResponse.json();

      // 2. Poll for status
      let attempts = 0;
      const maxAttempts = 60;
      let resultId: string | null = null;

      while (attempts < maxAttempts) {
        const statusResponse = await fetch(`/api/backend/result/status/${job_id}`);
        const statusData = await statusResponse.json();

        if (statusData.status === 'completed') {
          resultId = statusData.result_id || job_id;
          break;
        }
        if (statusData.status === 'failed') {
          throw new Error(statusData.error || 'Excel-Generierung fehlgeschlagen');
        }

        await new Promise((resolve) => setTimeout(resolve, 1000));
        attempts++;
      }

      if (!resultId) {
        throw new Error('Excel-Generierung Timeout');
      }

      // 3. Download the file
      const downloadResponse = await fetch(`/api/backend/result/${resultId}/download`);
      if (!downloadResponse.ok) {
        throw new Error('Excel-Download fehlgeschlagen');
      }

      const blob = await downloadResponse.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'FTAG_Machbarkeit.xlsx';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Download fehlgeschlagen');
    } finally {
      setIsDownloading(false);
    }
  }, [result]);

  // Sortable header
  function SortableHeader({ field, children }: { field: SortField; children: React.ReactNode }) {
    return (
      <TableHead
        className="cursor-pointer select-none"
        onClick={() => handleSort(field)}
        data-testid={`sort-${field}`}
      >
        <div className="flex items-center gap-1">
          {children}
          <ArrowUpDown className="size-3.5 text-muted-foreground" />
          {sortField === field && (
            <span className="text-xs">{sortDir === 'asc' ? '\u2191' : '\u2193'}</span>
          )}
        </div>
      </TableHead>
    );
  }

  if (allEntries.length === 0) {
    return (
      <div className="flex flex-col items-center py-12 text-center" data-testid="results-empty">
        <p className="text-muted-foreground">Keine Ergebnisse</p>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="step-results">
      {/* Header with filter bar and download button */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex flex-1 gap-3">
          {/* Text search */}
          <div className="relative flex-1 max-w-xs">
            <Search className="absolute left-2.5 top-2.5 size-4 text-muted-foreground" />
            <Input
              placeholder="Suchen..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-9"
              data-testid="search-input"
            />
          </div>

          {/* Confidence dropdown */}
          <Select value={confidenceFilter} onValueChange={(val) => setConfidenceFilter(val ?? 'all')}>
            <SelectTrigger className="w-[180px]" data-testid="confidence-filter">
              <SelectValue placeholder="Alle" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Alle</SelectItem>
              <SelectItem value="high">Hoch (&gt;={config.highThreshold}%)</SelectItem>
              <SelectItem value="medium">Mittel ({config.lowThreshold}-{config.highThreshold}%)</SelectItem>
              <SelectItem value="low">Niedrig (&lt;{config.lowThreshold}%)</SelectItem>
              <SelectItem value="gap">Gap</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {/* Excel download */}
        <Button
          variant="outline"
          className="gap-2"
          onClick={handleDownloadExcel}
          disabled={isDownloading}
          data-testid="download-excel-btn"
        >
          {isDownloading ? (
            <Loader2 className="size-4 animate-spin" />
          ) : (
            <Download className="size-4" />
          )}
          Excel herunterladen
        </Button>
      </div>

      {/* Filter summary chips */}
      <div className="flex flex-wrap gap-2" data-testid="filter-chips">
        <Badge className="bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400" data-testid="chip-high">
          {filterCounts.high} Hoch
        </Badge>
        <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400" data-testid="chip-medium">
          {filterCounts.medium} Mittel
        </Badge>
        <Badge className="bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400" data-testid="chip-low">
          {filterCounts.low} Niedrig
        </Badge>
        <Badge className="bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400" data-testid="chip-gap">
          {filterCounts.gap} Gap
        </Badge>
      </div>

      {/* Results table */}
      <div className="rounded-md border">
        <Table>
          <TableHeader>
            <TableRow>
              <SortableHeader field="nr">Nr</SortableHeader>
              <SortableHeader field="beschreibung">Anforderung</SortableHeader>
              <SortableHeader field="position">Position</SortableHeader>
              <SortableHeader field="produkt">Zugeordnetes Produkt</SortableHeader>
              <SortableHeader field="artikelnr">Artikelnr</SortableHeader>
              <SortableHeader field="konfidenz">Konfidenz</SortableHeader>
            </TableRow>
          </TableHeader>
          <TableBody>
            {sortedEntries.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="h-24 text-center text-muted-foreground">
                  Keine Treffer fuer die aktuelle Filterung
                </TableCell>
              </TableRow>
            ) : (
              sortedEntries.map((entry) => (
                <React.Fragment key={entry.nr}>
                  <TableRow
                    className={`cursor-pointer hover:bg-muted/50 ${
                      entry.status === 'unmatched' ? 'bg-red-50 dark:bg-red-950/20' : ''
                    } ${expandedRow === entry.nr ? 'bg-muted border-l-2 border-l-[hsl(var(--ftag-red,0_84%_44%))]' : ''}`}
                    onClick={() => onExpandRow(entry.nr)}
                    data-testid={`result-row-${entry.nr}`}
                  >
                    <TableCell className="font-medium">{entry.nr}</TableCell>
                    <TableCell title={entry.beschreibung}>
                      {truncate(entry.beschreibung, 60)}
                    </TableCell>
                    <TableCell>{entry.position}</TableCell>
                    <TableCell>
                      {entry.matched_products[0]?.bezeichnung || 'Kein Produkt'}
                    </TableCell>
                    <TableCell>
                      {entry.matched_products[0]?.artikelnr || '-'}
                    </TableCell>
                    <TableCell>
                      <ConfidenceBadge
                        confidence={entry.confidence}
                        highThreshold={config.highThreshold}
                        lowThreshold={config.lowThreshold}
                      />
                    </TableCell>
                  </TableRow>
                  {expandedRow === entry.nr && (
                    <TableRow data-testid={`result-detail-row-${entry.nr}`}>
                      <TableCell colSpan={6} className="p-0">
                        <ResultDetail entry={entry} config={config} />
                      </TableCell>
                    </TableRow>
                  )}
                </React.Fragment>
              ))
            )}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
