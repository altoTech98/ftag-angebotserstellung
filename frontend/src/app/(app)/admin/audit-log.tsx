'use client';

import { useState, useEffect, useTransition } from 'react';
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { getAuditLog } from '@/lib/actions/audit-actions';
import { listUsers } from '@/lib/actions/admin-actions';

const PAGE_SIZE = 50;

const ACTION_TYPES = [
  { value: '', label: 'Alle Aktionen' },
  { value: 'user_invited', label: 'Benutzer eingeladen' },
  { value: 'role_changed', label: 'Rolle geaendert' },
  { value: 'user_deactivated', label: 'Benutzer deaktiviert' },
  { value: 'user_activated', label: 'Benutzer aktiviert' },
  { value: 'settings_changed', label: 'Einstellungen geaendert' },
  { value: 'api_key_changed', label: 'API-Schluessel geaendert' },
];

interface AuditEntry {
  id: string;
  userId: string;
  action: string;
  details: string;
  targetId?: string | null;
  targetType?: string | null;
  createdAt: string | Date;
  user: { name: string; email: string };
}

interface UserOption {
  id: string;
  name: string;
}

export default function AuditLog() {
  const [entries, setEntries] = useState<AuditEntry[]>([]);
  const [total, setTotal] = useState(0);
  const [offset, setOffset] = useState(0);
  const [isPending, startTransition] = useTransition();

  // Filters
  const [filterUser, setFilterUser] = useState('');
  const [filterAction, setFilterAction] = useState('');
  const [filterFrom, setFilterFrom] = useState('');
  const [filterTo, setFilterTo] = useState('');

  // User list for filter dropdown
  const [userOptions, setUserOptions] = useState<UserOption[]>([]);

  useEffect(() => {
    // Load initial data
    fetchEntries(0);
    loadUsers();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function loadUsers() {
    startTransition(async () => {
      try {
        const result = await listUsers(undefined, 0, 200);
        setUserOptions(
          (result.users as unknown as UserOption[]).map((u) => ({
            id: u.id,
            name: u.name,
          }))
        );
      } catch {
        // Silently handle
      }
    });
  }

  function fetchEntries(newOffset: number) {
    startTransition(async () => {
      try {
        const result = await getAuditLog({
          userId: filterUser || undefined,
          action: filterAction || undefined,
          from: filterFrom ? new Date(filterFrom) : undefined,
          to: filterTo ? new Date(filterTo + 'T23:59:59') : undefined,
          offset: newOffset,
          limit: PAGE_SIZE,
        });
        setEntries(result.entries as unknown as AuditEntry[]);
        setTotal(result.total);
        setOffset(newOffset);
      } catch {
        // Silently handle
      }
    });
  }

  function handleFilter() {
    fetchEntries(0);
  }

  function handlePrev() {
    fetchEntries(Math.max(0, offset - PAGE_SIZE));
  }

  function handleNext() {
    fetchEntries(offset + PAGE_SIZE);
  }

  function formatDateTime(date: string | Date) {
    return new Date(date).toLocaleDateString('de-CH', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  return (
    <div className="space-y-4">
      {/* Filter bar */}
      <div className="flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <Label className="text-xs">Benutzer</Label>
          <Select value={filterUser} onValueChange={(v) => setFilterUser(v ?? '')}>
            <SelectTrigger className="w-[180px]">
              <SelectValue placeholder="Alle Benutzer" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="">Alle Benutzer</SelectItem>
              {userOptions.map((u) => (
                <SelectItem key={u.id} value={u.id}>
                  {u.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Aktion</Label>
          <Select value={filterAction} onValueChange={(v) => setFilterAction(v ?? '')}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Alle Aktionen" />
            </SelectTrigger>
            <SelectContent>
              {ACTION_TYPES.map((a) => (
                <SelectItem key={a.value} value={a.value}>
                  {a.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Von</Label>
          <Input
            type="date"
            value={filterFrom}
            onChange={(e) => setFilterFrom(e.target.value)}
            className="w-[150px]"
          />
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Bis</Label>
          <Input
            type="date"
            value={filterTo}
            onChange={(e) => setFilterTo(e.target.value)}
            className="w-[150px]"
          />
        </div>

        <Button variant="outline" onClick={handleFilter} disabled={isPending}>
          Filtern
        </Button>
      </div>

      {/* Audit log table */}
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Zeitpunkt</TableHead>
              <TableHead>Benutzer</TableHead>
              <TableHead>Aktion</TableHead>
              <TableHead>Details</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {entries.length === 0 ? (
              <TableRow>
                <TableCell
                  colSpan={4}
                  className="text-center text-muted-foreground py-8"
                >
                  Keine Eintraege gefunden
                </TableCell>
              </TableRow>
            ) : (
              entries.map((entry) => (
                <TableRow key={entry.id}>
                  <TableCell className="text-muted-foreground">
                    {formatDateTime(entry.createdAt)}
                  </TableCell>
                  <TableCell className="font-medium">
                    {entry.user.name}
                  </TableCell>
                  <TableCell>
                    {ACTION_TYPES.find((a) => a.value === entry.action)?.label ||
                      entry.action}
                  </TableCell>
                  <TableCell className="max-w-xs truncate">
                    {entry.details}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </div>

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} von {total}{' '}
            Eintraegen
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handlePrev}
              disabled={offset === 0 || isPending}
            >
              Zurueck
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleNext}
              disabled={offset + PAGE_SIZE >= total || isPending}
            >
              Weiter
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
