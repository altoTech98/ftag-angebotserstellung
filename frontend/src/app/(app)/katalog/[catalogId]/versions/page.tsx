import Link from 'next/link';
import { headers } from 'next/headers';
import { notFound } from 'next/navigation';
import { ArrowLeft } from 'lucide-react';
import { auth } from '@/lib/auth';
import prisma from '@/lib/prisma';
import { getCatalogVersions } from '@/lib/actions/catalog-actions';
import { CatalogVersionHistory } from '@/components/catalog/catalog-version-history';
import { Button } from '@/components/ui/button';

interface VersionsPageProps {
  params: Promise<{ catalogId: string }>;
}

export default async function VersionsPage({ params }: VersionsPageProps) {
  const { catalogId } = await params;

  const session = await auth.api.getSession({ headers: await headers() });
  let canManage = false;
  if (session) {
    const perm = await auth.api.userHasPermission({
      body: { userId: session.user.id, permissions: { catalog: ['update'] } },
    });
    canManage = !!perm.success;
  }

  const catalog = await prisma.catalog.findUnique({
    where: { id: catalogId },
  });
  if (!catalog) notFound();

  let versions: Awaited<ReturnType<typeof getCatalogVersions>> = [];
  try {
    versions = await getCatalogVersions(catalogId);
  } catch {
    // Will show empty state
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center gap-2 mb-1">
          <Link href={`/katalog/${catalogId}`}>
            <Button variant="ghost" size="sm" className="gap-1">
              <ArrowLeft className="size-3.5" />
              Zurueck
            </Button>
          </Link>
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Versionen &mdash; {catalog.name}
        </h1>
        <p className="text-muted-foreground">
          Versionsverlauf, Vergleich und Aktivierung
        </p>
      </div>

      <CatalogVersionHistory
        catalogId={catalogId}
        versions={versions as Parameters<typeof CatalogVersionHistory>[0]['versions']}
        canManage={canManage}
      />
    </div>
  );
}
