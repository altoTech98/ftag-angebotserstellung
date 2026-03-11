'use client';

import { useState, useTransition } from 'react';
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
import { Badge } from '@/components/ui/badge';
import {
  Dialog,
  DialogTrigger,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
  DialogClose,
} from '@/components/ui/dialog';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from '@/components/ui/select';
import { PencilIcon, PlusIcon, ShieldAlertIcon, ShieldCheckIcon } from 'lucide-react';
import {
  listUsers,
  inviteUser,
  updateUserRole,
  toggleUserBan,
} from '@/lib/actions/admin-actions';

const ROLES = [
  { value: 'viewer', label: 'Viewer' },
  { value: 'analyst', label: 'Analyst' },
  { value: 'manager', label: 'Manager' },
  { value: 'admin', label: 'Admin' },
];

const ROLE_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  admin: 'destructive',
  manager: 'default',
  analyst: 'secondary',
  viewer: 'outline',
};

const PAGE_SIZE = 50;

interface User {
  id: string;
  name: string;
  email: string;
  role: string;
  banned?: boolean | null;
  createdAt: string | Date;
}

interface UserManagementProps {
  initialUsers: Array<Record<string, unknown>>;
  initialTotal: number;
}

export default function UserManagement({
  initialUsers,
  initialTotal,
}: UserManagementProps) {
  const [users, setUsers] = useState<User[]>(initialUsers as unknown as User[]);
  const [total, setTotal] = useState(initialTotal);
  const [offset, setOffset] = useState(0);
  const [search, setSearch] = useState('');
  const [isPending, startTransition] = useTransition();

  // Invite dialog state
  const [inviteOpen, setInviteOpen] = useState(false);
  const [inviteRole, setInviteRole] = useState<string>('viewer');

  // Edit dialog state
  const [editUser, setEditUser] = useState<User | null>(null);
  const [editOpen, setEditOpen] = useState(false);
  const [editRole, setEditRole] = useState<string>('');

  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  function refreshUsers(searchVal?: string, newOffset?: number) {
    startTransition(async () => {
      try {
        const result = await listUsers(
          searchVal ?? search,
          newOffset ?? offset,
          PAGE_SIZE
        );
        setUsers(result.users as unknown as User[]);
        setTotal(result.total);
      } catch {
        // Silently handle refresh errors
      }
    });
  }

  function handleSearch(value: string) {
    setSearch(value);
    setOffset(0);
    refreshUsers(value, 0);
  }

  function handlePrev() {
    const newOffset = Math.max(0, offset - PAGE_SIZE);
    setOffset(newOffset);
    refreshUsers(search, newOffset);
  }

  function handleNext() {
    const newOffset = offset + PAGE_SIZE;
    setOffset(newOffset);
    refreshUsers(search, newOffset);
  }

  async function handleInvite(formData: FormData) {
    try {
      formData.set('role', inviteRole);
      await inviteUser(formData);
      setInviteOpen(false);
      setMessage({ type: 'success', text: 'Benutzer erfolgreich eingeladen' });
      refreshUsers();
    } catch (err) {
      setMessage({ type: 'error', text: (err as Error).message });
    }
  }

  async function handleEditSave() {
    if (!editUser) return;
    try {
      if (editRole !== editUser.role) {
        await updateUserRole(editUser.id, editRole);
      }
      setEditOpen(false);
      setEditUser(null);
      setMessage({ type: 'success', text: 'Benutzer aktualisiert' });
      refreshUsers();
    } catch (err) {
      setMessage({ type: 'error', text: (err as Error).message });
    }
  }

  async function handleToggleBan(user: User) {
    try {
      const newBan = !user.banned;
      await toggleUserBan(user.id, newBan);
      setMessage({
        type: 'success',
        text: newBan ? 'Benutzer deaktiviert' : 'Benutzer aktiviert',
      });
      refreshUsers();
    } catch (err) {
      setMessage({ type: 'error', text: (err as Error).message });
    }
  }

  function openEdit(user: User) {
    setEditUser(user);
    setEditRole(user.role);
    setEditOpen(true);
  }

  function formatDate(date: string | Date) {
    return new Date(date).toLocaleDateString('de-CH', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  }

  return (
    <div className="space-y-4">
      {/* Header with search and invite */}
      <div className="flex items-center justify-between gap-4">
        <Input
          placeholder="Benutzer suchen..."
          value={search}
          onChange={(e) => handleSearch(e.target.value)}
          className="max-w-xs"
        />
        <Dialog open={inviteOpen} onOpenChange={setInviteOpen}>
          <DialogTrigger
            render={(props) => (
              <Button {...props}>
                <PlusIcon data-icon="inline-start" />
                Benutzer einladen
              </Button>
            )}
          />
          <DialogContent className="sm:max-w-md">
            <DialogHeader>
              <DialogTitle>Benutzer einladen</DialogTitle>
              <DialogDescription>
                Neuen Benutzer mit E-Mail-Einladung hinzufuegen
              </DialogDescription>
            </DialogHeader>
            <form action={handleInvite} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="invite-name">Name</Label>
                <Input id="invite-name" name="name" required />
              </div>
              <div className="space-y-2">
                <Label htmlFor="invite-email">E-Mail</Label>
                <Input id="invite-email" name="email" type="email" required />
              </div>
              <div className="space-y-2">
                <Label>Rolle</Label>
                <Select value={inviteRole} onValueChange={(v) => v && setInviteRole(v)}>
                  <SelectTrigger className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {ROLES.map((r) => (
                      <SelectItem key={r.value} value={r.value}>
                        {r.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <DialogFooter>
                <DialogClose render={<Button variant="outline" />}>
                  Abbrechen
                </DialogClose>
                <Button type="submit">Einladen</Button>
              </DialogFooter>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Status message */}
      {message && (
        <div
          className={`rounded-lg border px-4 py-2 text-sm ${
            message.type === 'success'
              ? 'border-green-200 bg-green-50 text-green-800 dark:border-green-800 dark:bg-green-950 dark:text-green-200'
              : 'border-red-200 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950 dark:text-red-200'
          }`}
        >
          {message.text}
          <button
            onClick={() => setMessage(null)}
            className="ml-2 font-medium underline"
          >
            Schliessen
          </button>
        </div>
      )}

      {/* User table */}
      <div className="rounded-lg border border-border">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Name</TableHead>
              <TableHead>E-Mail</TableHead>
              <TableHead>Rolle</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Erstellt am</TableHead>
              <TableHead className="text-right">Aktionen</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {users.length === 0 ? (
              <TableRow>
                <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                  Keine Benutzer gefunden
                </TableCell>
              </TableRow>
            ) : (
              users.map((user) => (
                <TableRow key={user.id}>
                  <TableCell className="font-medium">{user.name}</TableCell>
                  <TableCell>{user.email}</TableCell>
                  <TableCell>
                    <Badge variant={ROLE_VARIANT[user.role] || 'outline'}>
                      {user.role}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge variant={user.banned ? 'outline' : 'secondary'}>
                      {user.banned ? 'Deaktiviert' : 'Aktiv'}
                    </Badge>
                  </TableCell>
                  <TableCell>{formatDate(user.createdAt)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex items-center justify-end gap-1">
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => openEdit(user)}
                        title="Bearbeiten"
                      >
                        <PencilIcon />
                      </Button>
                      <Button
                        variant="ghost"
                        size="icon-sm"
                        onClick={() => handleToggleBan(user)}
                        title={user.banned ? 'Aktivieren' : 'Deaktivieren'}
                      >
                        {user.banned ? <ShieldCheckIcon /> : <ShieldAlertIcon />}
                      </Button>
                    </div>
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
            {offset + 1}–{Math.min(offset + PAGE_SIZE, total)} von {total} Benutzern
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

      {/* Edit Dialog */}
      <Dialog open={editOpen} onOpenChange={setEditOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Benutzer bearbeiten</DialogTitle>
            <DialogDescription>
              {editUser?.name} ({editUser?.email})
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label>Rolle</Label>
              <Select value={editRole} onValueChange={(v) => v && setEditRole(v)}>
                <SelectTrigger className="w-full">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {ROLES.map((r) => (
                    <SelectItem key={r.value} value={r.value}>
                      {r.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>
          <DialogFooter>
            <DialogClose render={<Button variant="outline" />}>
              Abbrechen
            </DialogClose>
            <Button onClick={handleEditSave}>Speichern</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
