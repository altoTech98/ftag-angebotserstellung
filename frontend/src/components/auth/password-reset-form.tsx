"use client";

import { useState } from "react";
import { authClient } from "@/lib/auth-client";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Loader2, AlertCircle, CheckCircle2 } from "lucide-react";
import Link from "next/link";

type Step = "request" | "verify" | "success";

export function PasswordResetForm() {
  const [step, setStep] = useState<Step>("request");
  const [email, setEmail] = useState("");
  const [code, setCode] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleRequestCode(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const result = await authClient.emailOtp.sendVerificationOtp({
        email,
        type: "forget-password",
      });

      if (result.error) {
        setError("Code konnte nicht gesendet werden. Bitte versuchen Sie es erneut.");
      } else {
        setStep("verify");
      }
    } catch {
      setError("Code konnte nicht gesendet werden. Bitte versuchen Sie es erneut.");
    } finally {
      setLoading(false);
    }
  }

  async function handleVerifyAndReset(e: React.FormEvent) {
    e.preventDefault();
    setError("");

    if (newPassword !== confirmPassword) {
      setError("Passwoerter stimmen nicht ueberein.");
      return;
    }

    if (newPassword.length < 8) {
      setError("Passwort muss mindestens 8 Zeichen lang sein.");
      return;
    }

    setLoading(true);

    try {
      const result = await authClient.emailOtp.resetPassword({
        email,
        otp: code,
        password: newPassword,
      });

      if (result.error) {
        setError("Code ungueltig oder abgelaufen. Bitte versuchen Sie es erneut.");
      } else {
        setStep("success");
      }
    } catch {
      setError("Code ungueltig oder abgelaufen. Bitte versuchen Sie es erneut.");
    } finally {
      setLoading(false);
    }
  }

  if (step === "success") {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Passwort zurueckgesetzt</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert>
            <CheckCircle2 className="size-4" />
            <AlertDescription>
              Ihr Passwort wurde erfolgreich zurueckgesetzt.
            </AlertDescription>
          </Alert>
          <div className="text-center">
            <Link
              href="/login"
              className="text-sm text-primary hover:underline underline-offset-4"
            >
              Zurueck zur Anmeldung
            </Link>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (step === "verify") {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">Code eingeben</CardTitle>
          <CardDescription>
            Geben Sie den 6-stelligen Code ein, der an {email} gesendet wurde.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleVerifyAndReset} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="code">6-stelliger Code</Label>
              <Input
                id="code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                placeholder="000000"
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, "").slice(0, 6))}
                required
                autoComplete="one-time-code"
                className="text-center text-lg tracking-widest"
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="new-password">Neues Passwort</Label>
              <Input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                required
                autoComplete="new-password"
                minLength={8}
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="confirm-password">Passwort bestaetigen</Label>
              <Input
                id="confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                required
                autoComplete="new-password"
                minLength={8}
              />
            </div>

            {error && (
              <Alert variant="destructive">
                <AlertCircle className="size-4" />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}

            <Button type="submit" className="w-full" disabled={loading}>
              {loading && <Loader2 className="animate-spin" />}
              Passwort zuruecksetzen
            </Button>

            <div className="text-center">
              <Link
                href="/login"
                className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-4"
              >
                Zurueck zur Anmeldung
              </Link>
            </div>
          </form>
        </CardContent>
      </Card>
    );
  }

  // Step: request
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-xl">Passwort vergessen</CardTitle>
        <CardDescription>
          Geben Sie Ihre E-Mail-Adresse ein, um einen Code zum Zuruecksetzen zu erhalten.
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleRequestCode} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="reset-email">E-Mail</Label>
            <Input
              id="reset-email"
              type="email"
              placeholder="name@firma.ch"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              autoComplete="email"
            />
          </div>

          {error && (
            <Alert variant="destructive">
              <AlertCircle className="size-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          <Button type="submit" className="w-full" disabled={loading}>
            {loading && <Loader2 className="animate-spin" />}
            Code senden
          </Button>

          <div className="text-center">
            <Link
              href="/login"
              className="text-sm text-muted-foreground hover:text-foreground underline underline-offset-4"
            >
              Zurueck zur Anmeldung
            </Link>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
