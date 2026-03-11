import Link from 'next/link';
import { headers } from 'next/headers';
import { notFound } from 'next/navigation';
import { ArrowLeft, History } from 'lucide-react';
import { auth } from '@/lib/auth';
import prisma from '@/lib/prisma';
import { getCatalogProducts } from '@/lib/actions/catalog-actions';
import { CatalogStats } from '@/components/catalog/catalog-stats';
import { CatalogTable } from '@/components/catalog/catalog-table';
import { Button } from '@/components/ui/button';

interface CatalogDetailPageProps {
  params: Promise<{ catalogId: string }>;
}

export default async function CatalogDetailPage({ params }: CatalogDetailPageProps) {
  const { catalogId } = await params;

  const session = await auth.api.getSession({ headers: await headers() });
  let canEdit = false;
  if (session) {
    const perm = await auth.api.userHasPermission({
      body: { userId: session.user.id, permissions: { catalog: ['update'] } },
    });
    canEdit = !!perm.success;
  }

  // Load catalog with active version
  const catalog = await prisma.catalog.findUnique({
    where: { id: catalogId },
    include: {
      versions: {
        where: { isActive: true },
        take: 1,
      },
    },
  });

  if (!catalog) notFound();

  const activeVersion = catalog.versions[0] ?? null;

  // Load initial products
  let initialProducts: Array<{
    row_index: number;
    category: string;
    summary: string;
    fields: Record<string, unknown>;
    kostentraeger?: string;
    hasOverride: boolean;
    overrideAction: string | null;
    overrideId: string | null;
  }> = [];
  let initialTotal = 0;
  let initialPages = 0;
  let categories: string[] = [];

  try {
    const result = await getCatalogProducts(catalogId);
    if (!('error' in result)) {
      initialProducts = result.products as typeof initialProducts;
      initialTotal = result.total;
      initialPages = result.pages;
    }
  } catch {
    // Will show empty table
  }

  // Try to load categories from Python catalog info
  try {
    const PYTHON_BACKEND_URL =
      process.env.PYTHON_BACKEND_URL || 'http://localhost:8000';
    const PYTHON_SERVICE_KEY = process.env.PYTHON_SERVICE_KEY || '';
    const resp = await fetch(`${PYTHON_BACKEND_URL}/api/catalog/info`, {
      headers: { 'X-Service-Key': PYTHON_SERVICE_KEY },
      cache: 'no-store',
    });
    if (resp.ok) {
      const info = (await resp.json()) as {
        category_breakdown?: Record<string, number>;
      };
      if (info.category_breakdown) {
        categories = Object.keys(info.category_breakdown).sort();
      }
    }
  } catch {
    // Categories will be empty -- filter still works without
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <Link href="/katalog">
              <Button variant="ghost" size="sm" className="gap-1">
                <ArrowLeft className="size-3.5" />
                Zurueck
              </Button>
            </Link>
          </div>
          <h1 className="text-2xl font-semibold tracking-tight">
            {catalog.name}
          </h1>
          {catalog.description && (
            <p className="text-muted-foreground">{catalog.description}</p>
          )}
        </div>
        <Link href={`/katalog/${catalogId}/versions`}>
          <Button variant="outline" size="sm" className="gap-1.5">
            <History className="size-3.5" />
            Versionen
          </Button>
        </Link>
      </div>

      {/* Stats */}
      {activeVersion && (
        <CatalogStats
          totalProducts={activeVersion.totalProducts}
          mainProducts={activeVersion.mainProducts}
          accessoryProducts={activeVersion.totalProducts - activeVersion.mainProducts}
          categories={activeVersion.categories}
        />
      )}

      {/* Product table */}
      <CatalogTable
        catalogId={catalogId}
        initialProducts={initialProducts}
        initialTotal={initialTotal}
        initialPages={initialPages}
        categories={categories}
        canEdit={canEdit}
      />
    </div>
  );
}
