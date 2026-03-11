'use client';

import {
  Activity,
  CheckCircle,
  XCircle,
  FolderPlus,
  Upload,
  Database,
  UserPlus,
  Settings,
  Play,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import type { ActivityEntry } from '@/lib/actions/dashboard-actions';

const ACTION_CONFIG: Record<string, { icon: React.ReactNode; label: string }> = {
  analysis_started: { icon: <Play className="size-4" />, label: 'hat eine Analyse gestartet' },
  analysis_completed: {
    icon: <CheckCircle className="size-4" />,
    label: 'Analyse abgeschlossen',
  },
  analysis_failed: { icon: <XCircle className="size-4" />, label: 'Analyse fehlgeschlagen' },
  project_created: { icon: <FolderPlus className="size-4" />, label: 'Projekt erstellt' },
  file_uploaded: { icon: <Upload className="size-4" />, label: 'Datei hochgeladen' },
  catalog_updated: { icon: <Database className="size-4" />, label: 'Katalog aktualisiert' },
  user_invited: { icon: <UserPlus className="size-4" />, label: 'Benutzer eingeladen' },
  settings_changed: {
    icon: <Settings className="size-4" />,
    label: 'Einstellungen geaendert',
  },
};

function getActionConfig(action: string) {
  return (
    ACTION_CONFIG[action] ?? {
      icon: <Activity className="size-4" />,
      label: action,
    }
  );
}

function getInitials(name: string | null, email: string): string {
  if (name) {
    const parts = name.split(' ');
    return parts
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase() ?? '')
      .join('');
  }
  return email[0]?.toUpperCase() ?? '?';
}

function formatRelativeTime(date: Date): string {
  const now = new Date();
  const diffMs = now.getTime() - new Date(date).getTime();
  const diffMin = Math.floor(diffMs / 60000);
  const diffHr = Math.floor(diffMs / 3600000);
  const diffDays = Math.floor(diffMs / 86400000);

  if (diffMin < 1) return 'gerade eben';
  if (diffMin < 60) return `vor ${diffMin} Min.`;
  if (diffHr < 24) return `vor ${diffHr} Std.`;
  if (diffDays === 1) return 'gestern';
  if (diffDays < 7) return `vor ${diffDays} Tagen`;
  return new Date(date).toLocaleDateString('de-CH');
}

export function ActivityFeed({ entries }: { entries: ActivityEntry[] }) {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Letzte Aktivitaeten</CardTitle>
      </CardHeader>
      <CardContent>
        {entries.length === 0 ? (
          <p className="text-sm text-muted-foreground">Noch keine Aktivitaeten</p>
        ) : (
          <div className="space-y-4">
            {entries.map((entry) => {
              const config = getActionConfig(entry.action);
              const initials = getInitials(entry.user.name, entry.user.email);
              const displayName = entry.user.name || entry.user.email;

              return (
                <div key={entry.id} className="flex items-start gap-3">
                  <div className="flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-xs font-medium">
                    {initials}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm">
                      <span className="font-medium">{displayName}</span>{' '}
                      <span className="text-muted-foreground">{config.label}</span>
                    </p>
                    {entry.details && (
                      <p className="text-xs text-muted-foreground truncate">{entry.details}</p>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 shrink-0 text-muted-foreground">
                    {config.icon}
                    <span className="text-xs">{formatRelativeTime(entry.createdAt)}</span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
