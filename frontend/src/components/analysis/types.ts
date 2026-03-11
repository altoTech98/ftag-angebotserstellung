// WizardState managed by useReducer
export type WizardState = {
  currentStep: number; // 1-5
  completedSteps: Set<number>;
  selectedFileIds: string[];
  catalogId: string | null;
  config: {
    highThreshold: number; // default 90
    lowThreshold: number; // default 70
    validationPasses: number; // default 1
  };
  jobId: string | null;
  analysisId: string | null;
  analysisResult: AnalysisResult | null;
  isAnalyzing: boolean;
  error: string | null;
};

export type WizardAction =
  | { type: 'NEXT_STEP' }
  | { type: 'PREV_STEP' }
  | { type: 'GO_TO_STEP'; step: number }
  | { type: 'SET_FILES'; fileIds: string[] }
  | { type: 'SET_CATALOG'; catalogId: string }
  | { type: 'SET_CONFIG'; config: Partial<WizardState['config']> }
  | { type: 'START_ANALYSIS'; jobId: string; analysisId: string }
  | { type: 'SET_RESULT'; result: AnalysisResult }
  | { type: 'ANALYSIS_FAILED'; error: string }
  | { type: 'RESET_ERROR' };

// Backend data shapes (from fast_matcher.py)
export interface MatchEntry {
  status: 'matched' | 'partial' | 'unmatched';
  confidence: number; // 0-1 scale
  position: string;
  beschreibung: string;
  menge: number;
  einheit: string;
  matched_products: ProductDetail[];
  gap_items: string[];
  missing_info: { feld: string; benoetigt: string; vorhanden: string }[];
  reason: string;
  original_position: Record<string, unknown>;
  category: string;
}

export interface ProductDetail {
  artikelnr: string;
  bezeichnung: string;
  [key: string]: unknown;
}

export interface AnalysisResult {
  matched: MatchEntry[];
  partial: MatchEntry[];
  unmatched: MatchEntry[];
  summary: {
    total_positions: number;
    matched_count: number;
    partial_count: number;
    unmatched_count: number;
    match_rate: number;
  };
}

// File data shape matching what project detail page provides
export interface ProjectFile {
  id: string;
  name: string;
  size: number;
  contentType: string;
  downloadUrl: string;
  createdAt: Date | string;
}

// Wizard step definitions
export const WIZARD_STEPS = [
  { number: 1, label: 'Dateien' },
  { number: 2, label: 'Katalog' },
  { number: 3, label: 'Konfiguration' },
  { number: 4, label: 'Analyse' },
  { number: 5, label: 'Ergebnisse' },
] as const;

// Analysis progress stages (for step 4)
export const ANALYSIS_STAGES = [
  { key: 'parse', label: 'Dokument lesen', pattern: /Excel|PDF|Dokumente werden/ },
  { key: 'extract', label: 'Anforderungen extrahieren', pattern: /Projektmetadaten|KI analysiert|Anforderungen/ },
  { key: 'match', label: 'Produkte zuordnen', pattern: /Matching|Positionen|Dedupliziert/ },
  { key: 'generate', label: 'Ergebnis generieren', pattern: /Ergebnisse werden|Fertig/ },
] as const;

// Confidence level helpers
export type ConfidenceLevel = 'high' | 'medium' | 'low';
export function getConfidenceLevel(
  confidence: number,
  highThreshold: number = 90,
  lowThreshold: number = 70
): ConfidenceLevel {
  const pct = Math.round(confidence * 100);
  if (pct >= highThreshold) return 'high';
  if (pct >= lowThreshold) return 'medium';
  return 'low';
}
