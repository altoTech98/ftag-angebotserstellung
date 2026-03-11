import Link from 'next/link';
import { FolderPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ProjectCard, type ProjectCardData } from '@/components/projects/project-card';

interface ProjectListProps {
  projects: ProjectCardData[];
  onArchive?: (projectId: string) => void;
  onDelete?: (projectId: string) => void;
}

export function ProjectList({ projects, onArchive, onDelete }: ProjectListProps) {
  if (projects.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center rounded-lg border border-dashed border-border bg-muted/30 py-12 text-center">
        <FolderPlus className="mb-4 size-10 text-muted-foreground" />
        <p className="mb-2 text-sm font-medium text-muted-foreground">
          Keine Projekte vorhanden
        </p>
        <p className="mb-4 text-xs text-muted-foreground">
          Erstellen Sie ein neues Projekt, um loszulegen.
        </p>
        <Link href="/projekte/neu">
          <Button>Neues Projekt erstellen</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
      {projects.map((project) => (
        <ProjectCard
          key={project.id}
          project={project}
          onArchive={onArchive}
          onDelete={onDelete}
        />
      ))}
    </div>
  );
}
