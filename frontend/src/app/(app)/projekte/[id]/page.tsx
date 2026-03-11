import { notFound, redirect } from 'next/navigation';
import Link from 'next/link';
import { ChevronRight, BarChart3 } from 'lucide-react';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import prisma from '@/lib/prisma';
import { ProjectDetailClient } from './client';

interface PageProps {
  params: Promise<{ id: string }>;
}

export default async function ProjectDetailPage({ params }: PageProps) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) redirect('/auth/login');

  const { id } = await params;
  const userId = session.user.id;

  const project = await prisma.project.findUnique({
    where: { id },
    include: {
      owner: { select: { name: true } },
      files: {
        orderBy: { createdAt: 'desc' },
        select: {
          id: true,
          name: true,
          size: true,
          contentType: true,
          downloadUrl: true,
          createdAt: true,
        },
      },
      analyses: {
        orderBy: { createdAt: 'desc' },
        select: {
          id: true,
          status: true,
          startedAt: true,
          endedAt: true,
          createdAt: true,
        },
      },
      shares: {
        select: {
          userId: true,
          user: { select: { name: true, email: true } },
        },
      },
    },
  });

  if (!project) notFound();

  // Check access: must be owner or shared user
  const isOwner = project.ownerId === userId;
  const isShared = project.shares.some((s) => s.userId === userId);
  const isAdmin = session.user.role === 'admin';

  if (!isOwner && !isShared && !isAdmin) notFound();

  // Check if user can share (manager/admin with project:share permission)
  const canShare = isOwner || isAdmin;

  const deadlineStr = project.deadline
    ? project.deadline.toLocaleDateString('de-CH', {
        day: '2-digit',
        month: '2-digit',
        year: 'numeric',
      })
    : null;

  const statusLabel =
    project.status === 'archived' ? 'Archiviert' : 'Aktiv';
  const statusClass =
    project.status === 'archived'
      ? 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
      : 'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400';

  return (
    <div className="space-y-8">
      {/* Breadcrumb + Header */}
      <div>
        <nav className="mb-2 flex items-center gap-1 text-sm text-muted-foreground">
          <Link href="/projekte" className="hover:text-foreground">
            Projekte
          </Link>
          <ChevronRight className="size-3" />
          <span className="text-foreground">{project.name}</span>
        </nav>

        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">
              {project.name}
            </h1>
            <div className="mt-1 flex flex-wrap items-center gap-3 text-sm text-muted-foreground">
              {project.customer && <span>{project.customer}</span>}
              {deadlineStr && <span>Frist: {deadlineStr}</span>}
              <span
                className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${statusClass}`}
              >
                {statusLabel}
              </span>
            </div>
            {project.description && (
              <p className="mt-2 text-sm text-muted-foreground">
                {project.description}
              </p>
            )}
          </div>

          {/* Archive/Delete buttons rendered in client component */}
        </div>
      </div>

      {/* Client-side interactive sections */}
      <ProjectDetailClient
        project={{
          id: project.id,
          name: project.name,
          status: project.status,
          files: project.files,
          analyses: project.analyses,
          sharesCount: project.shares.length,
          canShare,
        }}
      />
    </div>
  );
}
