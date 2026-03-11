'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { Archive, Trash2, BarChart3, ChevronRight, Share2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FileDropzone } from '@/components/upload/file-dropzone';
import { FileList, type FileData } from '@/components/upload/file-list';
import { ArchiveDialog } from '@/components/projects/archive-dialog';
import { ShareDialog } from '@/components/projects/share-dialog';

interface AnalysisData {
  id: string;
  status: string;
  startedAt: Date | string | null;
  endedAt: Date | string | null;
  createdAt: Date | string;
}

interface ProjectDetailClientProps {
  project: {
    id: string;
    name: string;
    status: string;
    files: FileData[];
    analyses: AnalysisData[];
    sharesCount: number;
    canShare: boolean;
  };
}

function formatDateTime(date: Date | string | null): string {
  if (!date) return '-';
  const d = typeof date === 'string' ? new Date(date) : date;
  return d.toLocaleString('de-CH', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function analysisStatusBadge(status: string) {
  const styles: Record<string, string> = {
    pending: 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-400',
    running: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
    completed: 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
    failed: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
  };
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${styles[status] || styles.pending}`}
    >
      {status}
    </span>
  );
}

export function ProjectDetailClient({ project }: ProjectDetailClientProps) {
  const router = useRouter();
  const [archiveAction, setArchiveAction] = useState<'archive' | 'delete' | null>(null);
  const [shareOpen, setShareOpen] = useState(false);

  function handleFileChange() {
    router.refresh();
  }

  return (
    <>
      {/* Action buttons */}
      {project.status !== 'archived' && (
        <div className="flex items-center gap-2">
          {project.canShare && (
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShareOpen(true)}
            >
              <Share2 className="size-4" />
              Teilen
              {project.sharesCount > 0 && (
                <span className="ml-1 inline-flex size-5 items-center justify-center rounded-full bg-primary/10 text-xs font-medium text-primary">
                  {project.sharesCount}
                </span>
              )}
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => setArchiveAction('archive')}
          >
            <Archive className="size-4" />
            Archivieren
          </Button>
          <Button
            variant="destructive"
            size="sm"
            onClick={() => setArchiveAction('delete')}
          >
            <Trash2 className="size-4" />
            Loeschen
          </Button>
        </div>
      )}

      {/* Files Section */}
      <section className="space-y-4">
        <h2 className="text-lg font-semibold">Dateien</h2>
        <FileDropzone
          projectId={project.id}
          onFileUploaded={handleFileChange}
        />
        <FileList files={project.files} onFileDeleted={handleFileChange} />
      </section>

      {/* Analyses Section */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold">Analysen</h2>
          {project.status !== 'archived' && project.analyses.length > 0 && (
            <Link href={`/projekte/${project.id}/analyse`}>
              <Button variant="default" size="sm" className="gap-2">
                <BarChart3 className="size-4" />
                Neue Analyse
              </Button>
            </Link>
          )}
        </div>
        {project.analyses.length === 0 ? (
          <div className="flex flex-col items-center rounded-lg border border-dashed border-border bg-muted/30 py-8 text-center">
            <BarChart3 className="mb-3 size-8 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">
              Noch keine Analysen durchgefuehrt
            </p>
            {project.status !== 'archived' && (
              <Link href={`/projekte/${project.id}/analyse`} className="mt-3">
                <Button variant="default" className="gap-2">
                  <BarChart3 className="size-4" />
                  Neue Analyse starten
                </Button>
              </Link>
            )}
          </div>
        ) : (
          <ul className="divide-y divide-border rounded-lg border border-border">
            {project.analyses.map((analysis) => {
              const isCompleted = analysis.status === 'completed';
              const content = (
                <li
                  key={analysis.id}
                  className={`flex items-center justify-between px-4 py-3 ${
                    isCompleted ? 'cursor-pointer hover:bg-muted/50 transition-colors' : ''
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <BarChart3 className="size-4 text-muted-foreground" />
                    <div>
                      <div className="flex items-center gap-2">
                        {analysisStatusBadge(analysis.status)}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Gestartet: {formatDateTime(analysis.startedAt)}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {analysis.endedAt && (
                      <span className="text-xs text-muted-foreground">
                        Abgeschlossen: {formatDateTime(analysis.endedAt)}
                      </span>
                    )}
                    {isCompleted && (
                      <ChevronRight className="size-4 text-muted-foreground" />
                    )}
                  </div>
                </li>
              );

              if (isCompleted) {
                return (
                  <Link
                    key={analysis.id}
                    href={`/projekte/${project.id}/analyse?analysisId=${analysis.id}`}
                    className="block"
                  >
                    {content}
                  </Link>
                );
              }
              return <div key={analysis.id}>{content}</div>;
            })}
          </ul>
        )}
      </section>

      {/* Share Dialog */}
      <ShareDialog
        projectId={project.id}
        projectName={project.name}
        open={shareOpen}
        onOpenChange={setShareOpen}
      />

      {/* Archive/Delete Dialog */}
      {archiveAction && (
        <ArchiveDialog
          projectId={project.id}
          projectName={project.name}
          action={archiveAction}
          open={true}
          onOpenChange={(open) => {
            if (!open) setArchiveAction(null);
          }}
        />
      )}
    </>
  );
}
