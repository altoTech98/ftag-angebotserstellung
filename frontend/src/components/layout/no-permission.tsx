import { ShieldX } from "lucide-react";

export function NoPermission() {
  return (
    <div className="flex min-h-[60vh] flex-col items-center justify-center text-center">
      <ShieldX size={48} className="mb-4 text-muted-foreground" />
      <h2 className="text-2xl font-semibold">Keine Berechtigung</h2>
      <p className="mt-2 max-w-md text-muted-foreground">
        Sie haben keine Berechtigung fuer diese Seite. Bitte kontaktieren Sie
        Ihren Administrator.
      </p>
    </div>
  );
}
