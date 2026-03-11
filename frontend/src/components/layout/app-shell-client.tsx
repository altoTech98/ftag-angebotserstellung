"use client";

import { SessionWarningModal } from "@/components/auth/session-warning-modal";

interface AppShellClientProps {
  children: React.ReactNode;
}

/**
 * Client wrapper for the authenticated app layout.
 * Renders the session warning modal (with idle detection)
 * alongside the main app content.
 */
export function AppShellClient({ children }: AppShellClientProps) {
  return (
    <>
      <SessionWarningModal />
      {children}
    </>
  );
}
