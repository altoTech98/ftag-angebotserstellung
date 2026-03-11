'use client';

import Link from 'next/link';
import { Folder, FileText, BarChart3, Archive, Trash2, MoreVertical, Calendar } from 'lucide-react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
  CardAction,
} from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';

export interface ProjectCardData {
  id: string;
  name: string;
  customer: string | null;
  deadline: Date | string | null;
  status: string;
  owner: { name: string | null };
  _count: { files: number; analyses: number };
}

interface ProjectCardProps {
  project: ProjectCardData;
  onArchive?: (projectId: string) => void;
  onDelete?: (projectId: string) => void;
}

function formatDate(date: Date | string | null): string | null {
  if (!date) return null;
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleDateString('de-CH', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
}

function statusBadge(status: string) {
  const styles: Record<string, string> = {
    active: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    archived: 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400',
  };
  const labels: Record<string, string> = {
    active: 'Aktiv',
    archived: 'Archiviert',
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] || styles.active}`}
    >
      {labels[status] || status}
    </span>
  );
}

export function ProjectCard({ project, onArchive, onDelete }: ProjectCardProps) {
  return (
    <Card className="relative transition-shadow hover:shadow-md">
      <CardHeader>
        <div className="flex items-start justify-between gap-2">
          <Link
            href={`/projekte/${project.id}`}
            className="flex items-center gap-2 hover:underline"
          >
            <Folder className="size-4 text-primary" />
            <CardTitle className="line-clamp-1">{project.name}</CardTitle>
          </Link>
          {statusBadge(project.status)}
        </div>
        <CardAction>
          <DropdownMenu>
            <DropdownMenuTrigger>
              <Button variant="ghost" size="icon-xs">
                <MoreVertical className="size-4" />
                <span className="sr-only">Aktionen</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem
                onClick={() => onArchive?.(project.id)}
              >
                <Archive className="size-4" />
                Archivieren
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem
                variant="destructive"
                onClick={() => onDelete?.(project.id)}
              >
                <Trash2 className="size-4" />
                Loeschen
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </CardAction>
      </CardHeader>

      <CardContent>
        {project.customer && (
          <CardDescription className="line-clamp-1">
            {project.customer}
          </CardDescription>
        )}
        {project.deadline && (
          <div className="mt-1 flex items-center gap-1 text-xs text-muted-foreground">
            <Calendar className="size-3" />
            <span>Frist: {formatDate(project.deadline)}</span>
          </div>
        )}
      </CardContent>

      <CardFooter className="gap-4 text-xs text-muted-foreground">
        <div className="flex items-center gap-1">
          <FileText className="size-3.5" />
          <span>{project._count.files} Dateien</span>
        </div>
        <div className="flex items-center gap-1">
          <BarChart3 className="size-3.5" />
          <span>{project._count.analyses} Analysen</span>
        </div>
      </CardFooter>
    </Card>
  );
}
