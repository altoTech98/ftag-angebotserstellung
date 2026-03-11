import Link from 'next/link';
import { ChevronRight } from 'lucide-react';
import { ProjectForm } from '@/components/projects/project-form';

export default function NeuesProjektPage() {
  return (
    <div className="space-y-6">
      <div>
        <nav className="mb-2 flex items-center gap-1 text-sm text-muted-foreground">
          <Link href="/projekte" className="hover:text-foreground">
            Projekte
          </Link>
          <ChevronRight className="size-3" />
          <span className="text-foreground">Neues Projekt</span>
        </nav>
        <h1 className="text-2xl font-semibold tracking-tight">Neues Projekt</h1>
        <p className="text-muted-foreground">
          Erstellen Sie ein neues Projekt fuer eine Ausschreibung.
        </p>
      </div>

      <ProjectForm />
    </div>
  );
}
