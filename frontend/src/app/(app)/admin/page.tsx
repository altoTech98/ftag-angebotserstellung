import { headers } from "next/headers";
import { auth } from "@/lib/auth";
import { NoPermission } from "@/components/layout/no-permission";

export default async function AdminPage() {
  const session = await auth.api.getSession({
    headers: await headers(),
  });

  const hasAccess = await auth.api.userHasPermission({
    body: {
      userId: session!.user.id,
      permissions: { admin: ["access"] },
    },
  });

  if (!hasAccess.success) {
    return <NoPermission />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">
          Administration
        </h1>
        <p className="text-muted-foreground">
          Benutzerverwaltung und Systemeinstellungen
        </p>
      </div>
      <div className="rounded-lg border border-border bg-card p-6 text-card-foreground">
        <p className="text-sm text-muted-foreground">
          Admin-Bereich wird in Phase 15 implementiert
        </p>
      </div>
    </div>
  );
}
