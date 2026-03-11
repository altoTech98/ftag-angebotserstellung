"use client";

import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

function formatRemainingTime(ms: number): string {
  const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;

  if (minutes > 0) {
    return `${minutes} Minute${minutes !== 1 ? "n" : ""} und ${seconds} Sekunde${seconds !== 1 ? "n" : ""}`;
  }
  return `${seconds} Sekunde${seconds !== 1 ? "n" : ""}`;
}

interface SessionWarningModalProps {
  showWarning: boolean;
  remainingTime: number;
  extendSession: () => void;
}

export function SessionWarningModal({
  showWarning,
  remainingTime,
  extendSession,
}: SessionWarningModalProps) {
  function handleLogout() {
    window.location.href = "/login";
  }

  return (
    <Dialog open={showWarning}>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>Sitzung laeuft ab</DialogTitle>
          <DialogDescription>
            Ihre Sitzung laeuft in {formatRemainingTime(remainingTime)} ab.
            Moechten Sie die Sitzung verlaengern?
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <Button variant="outline" onClick={handleLogout}>
            Abmelden
          </Button>
          <Button onClick={extendSession}>Sitzung verlaengern</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
