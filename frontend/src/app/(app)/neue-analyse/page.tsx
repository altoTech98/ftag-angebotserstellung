import { headers } from "next/headers";
import { redirect } from "next/navigation";
import Link from "next/link";
import { BarChart3, Building2, Calendar, FolderOpen } from "lucide-react";
import { auth } from "@/lib/auth";
import prisma from "@/lib/prisma";
import { NoPermission } from "@/components/layout/no-permission";

export default async function NeueAnalysePage() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  if (!session) redirect('/login');

  const hasAccess = await auth.api.userHasPermission({
    body: {
      userId: session.user.id,
      permissions: { analysis: ["create"] },
    },
  });

  if (!hasAccess.success) {
    return <NoPermission />;
  }

  const userId = session.user.id;

  const projects = await prisma.project.findMany({
    where: {
      OR: [
        { ownerId: userId },
        { shares: { some: { userId } } },
      ],
      status: { not: 'archived' },
    },
    orderBy: { updatedAt: 'desc' },
    select: { id: true, name: true, customer: true, updatedAt: true },
  });

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Neue Analyse starten</h1>
        <p className="text-muted-foreground">
          Waehlen Sie ein Projekt fuer die Analyse
        </p>
      </div>

      {projects.length === 0 ? (
        <div className="rounded-lg border border-border bg-card p-8 text-center text-card-foreground">
          <FolderOpen className="mx-auto mb-3 size-10 text-muted-foreground" />
          <p className="text-sm text-muted-foreground mb-4">
            Keine Projekte vorhanden
          </p>
          <Link
            href="/projekte"
            className="inline-flex items-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
          >
            Projekt erstellen
          </Link>
        </div>
      ) : (
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {projects.map((project) => (
            <Link
              key={project.id}
              href={`/projekte/${project.id}/analyse`}
              className="group rounded-lg border border-border bg-card p-4 text-card-foreground transition-colors hover:border-primary/50 hover:bg-accent/50"
            >
              <div className="flex items-start gap-3">
                <BarChart3 className="mt-0.5 size-5 text-primary shrink-0" />
                <div className="min-w-0">
                  <h3 className="font-medium truncate group-hover:text-primary">
                    {project.name}
                  </h3>
                  {project.customer && (
                    <p className="mt-1 flex items-center gap-1.5 text-sm text-muted-foreground truncate">
                      <Building2 className="size-3.5 shrink-0" />
                      {project.customer}
                    </p>
                  )}
                  <p className="mt-1 flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Calendar className="size-3 shrink-0" />
                    {new Date(project.updatedAt).toLocaleDateString('de-CH')}
                  </p>
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
