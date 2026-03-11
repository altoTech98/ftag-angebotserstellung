import Link from 'next/link';
import { redirect } from 'next/navigation';
import { Plus } from 'lucide-react';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import prisma from '@/lib/prisma';
import { Button } from '@/components/ui/button';
import { ProjectList } from '@/components/projects/project-list';

interface PageProps {
  searchParams: Promise<{ archiv?: string }>;
}

export default async function ProjektePage({ searchParams }: PageProps) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) redirect('/auth/login');

  const params = await searchParams;
  const showArchived = params.archiv === 'true';
  const userId = session.user.id;

  const projects = await prisma.project.findMany({
    where: {
      OR: [
        { ownerId: userId },
        { shares: { some: { userId } } },
      ],
      status: showArchived ? 'archived' : { not: 'archived' },
    },
    include: {
      owner: { select: { name: true } },
      _count: { select: { files: true, analyses: true } },
    },
    orderBy: { updatedAt: 'desc' },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {showArchived ? 'Archivierte Projekte' : 'Projekte'}
          </h1>
          <p className="text-muted-foreground">
            {showArchived
              ? 'Archivierte Projekte anzeigen'
              : 'Projektuebersicht und Verwaltung'}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {showArchived ? (
            <Link href="/projekte">
              <Button variant="outline">Aktive Projekte</Button>
            </Link>
          ) : (
            <Link href="/projekte?archiv=true">
              <Button variant="outline">Archiv</Button>
            </Link>
          )}
          <Link href="/projekte/neu">
            <Button>
              <Plus className="size-4" />
              Neues Projekt
            </Button>
          </Link>
        </div>
      </div>

      <ProjectList projects={projects} />
    </div>
  );
}
