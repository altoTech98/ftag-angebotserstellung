'use client';

import { useTransition, useState } from 'react';
import { useRouter } from 'next/navigation';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { createProject } from '@/lib/actions/project-actions';

export function ProjectForm() {
  const router = useRouter();
  const [isPending, startTransition] = useTransition();
  const [error, setError] = useState<string | null>(null);

  function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);

    const form = e.currentTarget;
    const formData = new FormData(form);
    const name = formData.get('name') as string;

    if (!name || name.trim().length === 0) {
      setError('Projektname ist erforderlich');
      return;
    }

    startTransition(async () => {
      try {
        await createProject(formData);
        router.push('/projekte');
      } catch (err) {
        setError(
          err instanceof Error ? err.message : 'Fehler beim Erstellen des Projekts'
        );
      }
    });
  }

  return (
    <form onSubmit={handleSubmit} className="max-w-lg space-y-6">
      {error && (
        <div className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      <div className="space-y-2">
        <Label htmlFor="name">
          Projektname <span className="text-destructive">*</span>
        </Label>
        <Input
          id="name"
          name="name"
          placeholder="z.B. Ausschreibung Gemeinde Buochs"
          required
          autoFocus
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="customer">Kunde</Label>
        <Input
          id="customer"
          name="customer"
          placeholder="z.B. Gemeinde Buochs"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="deadline">Frist</Label>
        <Input
          id="deadline"
          name="deadline"
          type="date"
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Beschreibung</Label>
        <textarea
          id="description"
          name="description"
          rows={3}
          placeholder="Optionale Beschreibung zum Projekt..."
          className="w-full rounded-lg border border-input bg-transparent px-2.5 py-2 text-sm transition-colors outline-none placeholder:text-muted-foreground focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 dark:bg-input/30"
        />
      </div>

      <div className="flex items-center gap-3">
        <Button type="submit" disabled={isPending}>
          {isPending ? 'Wird erstellt...' : 'Projekt erstellen'}
        </Button>
        <Button
          type="button"
          variant="outline"
          onClick={() => router.push('/projekte')}
          disabled={isPending}
        >
          Abbrechen
        </Button>
      </div>
    </form>
  );
}
