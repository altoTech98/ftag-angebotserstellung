import Link from 'next/link';
import { headers } from 'next/headers';
import { Database, ArrowRight, Calendar, FileText, Package } from 'lucide-react';
import { auth } from '@/lib/auth';
import { getCatalogs } from '@/lib/actions/catalog-actions';
import { CatalogUpload } from '@/components/catalog/catalog-upload';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

export default async function KatalogPage() {
  const session = await auth.api.getSession({ headers: await headers() });

  let canUpload = false;
  if (session) {
    const perm = await auth.api.userHasPermission({
      body: { userId: session.user.id, permissions: { catalog: ['upload'] } },
    });
    canUpload = !!perm.success;
  }

  let catalogs: Awaited<ReturnType<typeof getCatalogs>> = [];
  try {
    catalogs = await getCatalogs();
  } catch {
    // User not authenticated or no permission -- show empty state
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Katalogverwaltung
        </h1>
        <p className="text-muted-foreground">
          Produktkataloge hochladen, durchsuchen und verwalten
        </p>
      </div>

      {/* Upload section */}
      <CatalogUpload canUpload={canUpload} />

      {/* Catalog list */}
      {catalogs.length === 0 ? (
        <Card data-testid="empty-state">
          <CardContent className="flex flex-col items-center py-12 text-center">
            <Database className="mb-4 size-12 text-muted-foreground" />
            <h3 className="mb-1 text-lg font-medium">
              Noch keine Kataloge vorhanden
            </h3>
            <p className="text-sm text-muted-foreground">
              {canUpload
                ? 'Laden Sie einen Produktkatalog als Excel oder CSV hoch, um zu beginnen.'
                : 'Es wurden noch keine Kataloge hochgeladen.'}
            </p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4" data-testid="catalog-list">
          {catalogs.map((catalog) => {
            const activeVersion = catalog.versions[0] ?? null;

            return (
              <Card key={catalog.id} data-testid={`catalog-card-${catalog.id}`}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <Database className="size-5 text-primary" />
                        {catalog.name}
                        {activeVersion && (
                          <Badge variant="secondary">
                            v{activeVersion.versionNum}
                          </Badge>
                        )}
                      </CardTitle>
                      {catalog.description && (
                        <CardDescription>{catalog.description}</CardDescription>
                      )}
                    </div>
                    <div className="flex gap-2">
                      <Link href={`/katalog/${catalog.id}/versions`}>
                        <Button variant="outline" size="sm">
                          Versionen
                        </Button>
                      </Link>
                      <Link href={`/katalog/${catalog.id}`}>
                        <Button size="sm" className="gap-1">
                          Produkte
                          <ArrowRight className="size-3.5" />
                        </Button>
                      </Link>
                    </div>
                  </div>
                </CardHeader>
                {activeVersion && (
                  <CardContent>
                    <div className="flex flex-wrap gap-4 text-sm text-muted-foreground">
                      <span className="flex items-center gap-1.5">
                        <Package className="size-3.5" />
                        {activeVersion.totalProducts} Produkte
                      </span>
                      <span className="flex items-center gap-1.5">
                        <FileText className="size-3.5" />
                        {activeVersion.fileName}
                      </span>
                      <span className="flex items-center gap-1.5">
                        <Calendar className="size-3.5" />
                        {new Date(activeVersion.createdAt).toLocaleDateString(
                          'de-CH'
                        )}
                      </span>
                    </div>
                  </CardContent>
                )}
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
