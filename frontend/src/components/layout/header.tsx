"use client";

import { Bell, Menu } from "lucide-react";
import { Breadcrumbs } from "@/components/layout/breadcrumbs";
import { UserMenu } from "@/components/layout/user-menu";
import { useSidebarMobile } from "@/components/layout/sidebar";

interface HeaderProps {
  user: {
    name: string;
    email: string;
  };
}

export function Header({ user }: HeaderProps) {
  const { setMobileOpen } = useSidebarMobile();

  return (
    <header className="sticky top-0 z-40 flex h-14 items-center justify-between border-b border-border bg-background px-4">
      {/* Left: mobile hamburger + breadcrumbs */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => setMobileOpen(true)}
          className="rounded-md p-1.5 text-muted-foreground transition-colors hover:bg-accent hover:text-foreground md:hidden"
          aria-label="Menue oeffnen"
        >
          <Menu size={20} />
        </button>
        <Breadcrumbs />
      </div>

      {/* Right: notification bell + user menu */}
      <div className="flex items-center gap-3">
        <button
          disabled
          className="rounded-md p-1.5 text-muted-foreground/40 cursor-not-allowed"
          title="Kommt bald"
          aria-label="Benachrichtigungen (kommt bald)"
        >
          <Bell size={18} />
        </button>
        <UserMenu user={user} />
      </div>
    </header>
  );
}
