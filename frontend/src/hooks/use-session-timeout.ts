"use client";

import { useState, useEffect, useCallback, useRef } from "react";

const ACTIVITY_EVENTS = ["mousedown", "keydown", "scroll", "touchstart"];
const WARNING_BEFORE_MS = 5 * 60 * 1000; // 5 minutes before expiry
const COUNTDOWN_INTERVAL_MS = 1000; // Update countdown every second

/**
 * Tracks user activity and triggers a session timeout warning
 * 5 minutes before the session expires.
 *
 * @param expiresInMs - Session timeout in milliseconds (default: 8 hours)
 * @returns showWarning, extendSession callback, remainingTime in ms
 */
export function useSessionTimeout(expiresInMs: number = 8 * 60 * 60 * 1000) {
  const [showWarning, setShowWarning] = useState(false);
  const [remainingTime, setRemainingTime] = useState(WARNING_BEFORE_MS);

  const warningTimer = useRef<ReturnType<typeof setTimeout>>(null);
  const expireTimer = useRef<ReturnType<typeof setTimeout>>(null);
  const countdownInterval = useRef<ReturnType<typeof setInterval>>(null);
  const expiresAt = useRef<number>(Date.now() + expiresInMs);

  const clearAllTimers = useCallback(() => {
    if (warningTimer.current) clearTimeout(warningTimer.current);
    if (expireTimer.current) clearTimeout(expireTimer.current);
    if (countdownInterval.current) clearInterval(countdownInterval.current);
  }, []);

  const resetTimers = useCallback(() => {
    clearAllTimers();
    setShowWarning(false);

    const now = Date.now();
    expiresAt.current = now + expiresInMs;

    // Set warning timer (fires 5 min before expiry)
    warningTimer.current = setTimeout(() => {
      setShowWarning(true);
      setRemainingTime(WARNING_BEFORE_MS);

      // Start countdown
      countdownInterval.current = setInterval(() => {
        const remaining = expiresAt.current - Date.now();
        if (remaining <= 0) {
          clearAllTimers();
          window.location.href = "/login?expired=true";
        } else {
          setRemainingTime(remaining);
        }
      }, COUNTDOWN_INTERVAL_MS);
    }, expiresInMs - WARNING_BEFORE_MS);

    // Set expire timer (hard redirect)
    expireTimer.current = setTimeout(() => {
      clearAllTimers();
      window.location.href = "/login?expired=true";
    }, expiresInMs);
  }, [expiresInMs, clearAllTimers]);

  const extendSession = useCallback(async () => {
    // Call Better Auth to refresh the server session
    await fetch("/api/auth/session", {
      method: "GET",
      credentials: "include",
    });
    resetTimers();
  }, [resetTimers]);

  useEffect(() => {
    resetTimers();

    const handler = () => {
      // Only reset timers if warning is not showing
      // (user must explicitly click Extend to dismiss warning)
      if (!showWarning) {
        resetTimers();
      }
    };

    ACTIVITY_EVENTS.forEach((e) =>
      document.addEventListener(e, handler, { passive: true })
    );

    return () => {
      ACTIVITY_EVENTS.forEach((e) => document.removeEventListener(e, handler));
      clearAllTimers();
    };
  }, [resetTimers, clearAllTimers, showWarning]);

  return { showWarning, extendSession, remainingTime };
}
