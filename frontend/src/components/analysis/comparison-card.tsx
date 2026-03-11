'use client';

import { CheckCircle, AlertTriangle, XCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Separator } from '@/components/ui/separator';
import type { MatchEntry } from '@/components/analysis/types';

interface ComparisonCardProps {
  entry: MatchEntry;
}

/** Extract display-worthy fields from a generic record */
function extractFields(obj: Record<string, unknown>): { key: string; value: string }[] {
  const fields: { key: string; value: string }[] = [];
  for (const [key, value] of Object.entries(obj)) {
    if (value === null || value === undefined || value === '') continue;
    if (typeof value === 'object') continue; // skip nested objects
    fields.push({ key, value: String(value) });
  }
  return fields;
}

/** Check if two values are compatible (simple string similarity) */
function valuesMatch(reqValue: string, prodValue: string): boolean {
  const a = reqValue.toLowerCase().trim();
  const b = prodValue.toLowerCase().trim();
  if (a === b) return true;
  if (a.includes(b) || b.includes(a)) return true;
  return false;
}

/** Try to find matching product field for a requirement field */
function findMatchingKey(
  reqKey: string,
  productFields: { key: string; value: string }[]
): { key: string; value: string } | null {
  const reqLower = reqKey.toLowerCase();
  for (const pf of productFields) {
    if (pf.key.toLowerCase() === reqLower) return pf;
    // Partial match
    if (
      pf.key.toLowerCase().includes(reqLower) ||
      reqLower.includes(pf.key.toLowerCase())
    ) {
      return pf;
    }
  }
  return null;
}

export function ComparisonCard({ entry }: ComparisonCardProps) {
  const isGap = entry.status === 'unmatched' || entry.matched_products.length === 0;

  if (isGap) {
    return (
      <Card data-testid="comparison-card-gap">
        <CardHeader>
          <CardTitle>Abgelehnte Produkte</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {entry.gap_items.length > 0 ? (
            <ul className="space-y-2">
              {entry.gap_items.slice(0, 3).map((item, idx) => (
                <li
                  key={idx}
                  className="flex items-start gap-2 text-sm"
                  data-testid={`gap-item-${idx}`}
                >
                  <XCircle className="mt-0.5 size-4 shrink-0 text-red-500" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-muted-foreground">
              Kein passendes Produkt gefunden
            </p>
          )}
        </CardContent>
      </Card>
    );
  }

  // Matched/partial: two-column comparison
  const reqFields = extractFields(entry.original_position);
  const product = entry.matched_products[0];
  const productRecord: Record<string, unknown> = { ...product };
  const productFields = extractFields(productRecord);

  // Build comparison rows
  const usedProductKeys = new Set<string>();
  const rows: {
    reqKey: string;
    reqValue: string;
    prodKey: string | null;
    prodValue: string | null;
    matches: boolean;
  }[] = [];

  for (const rf of reqFields) {
    const matchedProd = findMatchingKey(rf.key, productFields);
    if (matchedProd) {
      usedProductKeys.add(matchedProd.key);
      rows.push({
        reqKey: rf.key,
        reqValue: rf.value,
        prodKey: matchedProd.key,
        prodValue: matchedProd.value,
        matches: valuesMatch(rf.value, matchedProd.value),
      });
    } else {
      rows.push({
        reqKey: rf.key,
        reqValue: rf.value,
        prodKey: null,
        prodValue: null,
        matches: false,
      });
    }
  }

  // Add unmatched product fields
  for (const pf of productFields) {
    if (!usedProductKeys.has(pf.key)) {
      rows.push({
        reqKey: '',
        reqValue: '',
        prodKey: pf.key,
        prodValue: pf.value,
        matches: false,
      });
    }
  }

  return (
    <Card data-testid="comparison-card">
      <CardHeader>
        <div className="grid grid-cols-2 gap-4">
          <CardTitle>Anforderung</CardTitle>
          <CardTitle>Produkt</CardTitle>
        </div>
      </CardHeader>
      <CardContent className="space-y-0">
        {rows.map((row, idx) => (
          <div key={idx}>
            {idx > 0 && <Separator className="my-2" />}
            <div className="grid grid-cols-[1fr_auto_1fr] gap-2 py-1" data-testid={`comparison-row-${idx}`}>
              {/* Requirement side */}
              <div className="text-sm">
                {row.reqKey && (
                  <>
                    <span className="font-medium text-muted-foreground">{row.reqKey}: </span>
                    <span>{row.reqValue}</span>
                  </>
                )}
              </div>

              {/* Match indicator */}
              <div className="flex items-center justify-center">
                {row.reqKey && row.prodKey ? (
                  row.matches ? (
                    <CheckCircle className="size-4 text-green-500" data-testid="match-indicator-check" />
                  ) : (
                    <AlertTriangle className="size-4 text-yellow-500" data-testid="match-indicator-warn" />
                  )
                ) : (
                  <span className="size-4" />
                )}
              </div>

              {/* Product side */}
              <div className="text-sm">
                {row.prodKey && (
                  <>
                    <span className="font-medium text-muted-foreground">{row.prodKey}: </span>
                    <span>{row.prodValue}</span>
                  </>
                )}
              </div>
            </div>
          </div>
        ))}

        {rows.length === 0 && (
          <p className="py-4 text-center text-sm text-muted-foreground">
            Keine Felder zum Vergleichen verfuegbar
          </p>
        )}
      </CardContent>
    </Card>
  );
}
