import { notFound, redirect } from 'next/navigation';
import Link from 'next/link';
import { ChevronRight } from 'lucide-react';
import { auth } from '@/lib/auth';
import { headers } from 'next/headers';
import prisma from '@/lib/prisma';
import { AnalyseWizardClient } from './client';
import type { AnalysisResult } from '@/components/analysis/types';

interface PageProps {
  params: Promise<{ id: string }>;
  searchParams: Promise<{ analysisId?: string }>;
}

export default async function AnalysePage({ params, searchParams }: PageProps) {
  const session = await auth.api.getSession({ headers: await headers() });
  if (!session) redirect('/login');

  // Permission check: analysis:create
  const hasPermission = await auth.api.userHasPermission({
    headers: await headers(),
    body: {
      permissions: {
        analysis: ['create'],
      },
    },
  });
  if (!hasPermission?.success) redirect('/projekte');

  const { id } = await params;
  const { analysisId } = await searchParams;
  const userId = session.user.id;

  const project = await prisma.project.findUnique({
    where: { id },
    include: {
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
      shares: {
        select: { userId: true },
      },
    },
  });

  if (!project) notFound();

  // Access check: owner, shared, or admin
  const isOwner = project.ownerId === userId;
  const isShared = project.shares.some((s: { userId: string }) => s.userId === userId);
  const isAdmin = session.user.role === 'admin';

  if (!isOwner && !isShared && !isAdmin) notFound();

  // If analysisId is provided, load the saved result
  let initialResult: AnalysisResult | null = null;
  if (analysisId) {
    const analysis = await prisma.analysis.findUnique({
      where: { id: analysisId },
    });
    if (analysis && analysis.projectId === id && analysis.result) {
      initialResult = analysis.result as unknown as AnalysisResult;
    }
  }

  const breadcrumbTitle = initialResult ? 'Analyseergebnis' : 'Neue Analyse';

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <nav className="flex items-center gap-1 text-sm text-muted-foreground">
        <Link href="/projekte" className="hover:text-foreground">
          Projekte
        </Link>
        <ChevronRight className="size-3" />
        <Link
          href={`/projekte/${project.id}`}
          className="hover:text-foreground"
        >
          {project.name}
        </Link>
        <ChevronRight className="size-3" />
        <span className="text-foreground">{breadcrumbTitle}</span>
      </nav>

      <h1 className="text-2xl font-semibold tracking-tight">{breadcrumbTitle}</h1>

      <AnalyseWizardClient
        project={{
          id: project.id,
          name: project.name,
          files: project.files,
        }}
        initialResult={initialResult}
      />
    </div>
  );
}
