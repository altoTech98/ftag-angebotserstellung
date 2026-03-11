import { headers } from "next/headers";
import { auth } from "@/lib/auth";
import { NoPermission } from "@/components/layout/no-permission";
import { listUsers, getSystemSettings } from "@/lib/actions/admin-actions";
import AdminClient from "./client";

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

  const [usersResult, settings] = await Promise.all([
    listUsers(),
    getSystemSettings(),
  ]);

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
      <AdminClient
        initialUsers={usersResult.users}
        initialTotal={usersResult.total}
        initialSettings={settings}
      />
    </div>
  );
}
