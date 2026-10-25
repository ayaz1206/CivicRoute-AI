"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { Container } from "@/components/ui/Page";
import { Card, CardBody } from "@/components/ui/Card";
import { Field, Input } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Icon } from "@/components/ui/Icon";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const user = await login(email, password);
      // Staff land on the dashboard.
      router.push("/staff");
      router.refresh();
      void user;
    } catch (err) {
      setError(
        err instanceof Error
          ? err.message
          : "Login failed. Check your credentials.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <Container size="narrow" className="py-8">
      <div className="mx-auto max-w-sm">
        <div className="mb-6 flex flex-col items-center text-center">
          <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brand-600 text-white shadow-sm">
            <Icon.shield className="h-6 w-6" />
          </span>
          <h1 className="mt-4 text-2xl font-bold tracking-tight text-content">
            Staff sign in
          </h1>
          <p className="mt-1 text-sm text-content-muted">
            Staff and administrators only. Residents don&apos;t need an account.
          </p>
        </div>

        <Card>
          <CardBody>
            {error && (
              <Alert tone="error" className="mb-4">
                {error}
              </Alert>
            )}
            <form onSubmit={onSubmit} className="flex flex-col gap-4">
              <Field label="Email" htmlFor="email" required>
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  autoComplete="email"
                  placeholder="you@city.gov"
                />
              </Field>
              <Field label="Password" htmlFor="password" required>
                <Input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                />
              </Field>
              <Button type="submit" loading={busy} className="mt-1 w-full">
                {busy ? "Signing in…" : "Sign in"}
              </Button>
            </form>
          </CardBody>
        </Card>
      </div>
    </Container>
  );
}
