"use client";

import { Sidebar, SidebarProvider } from "@/components/layout/sidebar";
import { Header } from "@/components/layout/header";
import { AppShellClient } from "@/components/layout/app-shell-client";

interface AppShellProps {
  user: {
    id: string;
    name: string;
    email: string;
    role: string;
  };
  children: React.ReactNode;
}

export function AppShell({ user, children }: AppShellProps) {
  return (
    <SidebarProvider>
      <AppShellClient>
        <div className="flex h-screen overflow-hidden">
          <Sidebar user={user} />
          <div className="flex flex-1 flex-col overflow-hidden">
            <Header user={user} />
            <main className="flex-1 overflow-y-auto p-6">{children}</main>
          </div>
        </div>
      </AppShellClient>
    </SidebarProvider>
  );
}
