"use client";

import { useSessionTimeout } from "@/hooks/use-session-timeout";
import { SessionWarningModal } from "@/components/auth/session-warning-modal";

interface AppShellClientProps {
  children: React.ReactNode;
}

/**
 * Client wrapper for the authenticated app layout.
 * Calls useSessionTimeout at the shell level and passes state
 * as props to SessionWarningModal (pure presentational).
 */
export function AppShellClient({ children }: AppShellClientProps) {
  const { showWarning, extendSession, remainingTime } = useSessionTimeout();

  return (
    <>
      <SessionWarningModal
        showWarning={showWarning}
        remainingTime={remainingTime}
        extendSession={extendSession}
      />
      {children}
    </>
  );
}
