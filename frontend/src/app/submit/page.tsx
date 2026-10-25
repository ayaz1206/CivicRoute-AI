"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import {
  listCities,
  submitComplaint,
  type City,
  type SubmitResult,
} from "@/lib/api";
import { Container, PageHeader } from "@/components/ui/Page";
import { Card, CardBody } from "@/components/ui/Card";
import { Field, Input, Textarea, Select } from "@/components/ui/Field";
import { Button } from "@/components/ui/Button";
import { Alert } from "@/components/ui/Alert";
import { Icon } from "@/components/ui/Icon";

export default function SubmitPage() {
  const [cities, setCities] = useState<City[]>([]);
  const [cityId, setCityId] = useState<number | "">("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [location, setLocation] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<SubmitResult | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    listCities()
      .then((c) => {
        setCities(c);
        if (c.length > 0) setCityId(c[0].id);
      })
      .catch(() => setError("Could not load cities. Is the backend running?"));
  }, []);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    if (cityId === "") {
      setError("Please choose a city.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await submitComplaint({
        city_id: cityId,
        title,
        description,
        reporter_name: name || undefined,
        reporter_email: email || undefined,
        location_text: location || undefined,
      });
      setResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Submission failed.");
    } finally {
      setSubmitting(false);
    }
  }

  // ---- Confirmation state ----
  if (result) {
    return (
      <Container size="narrow">
        <Card>
          <CardBody className="flex flex-col items-center gap-4 py-10 text-center">
            <span className="flex h-14 w-14 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 dark:bg-emerald-500/15 dark:text-emerald-400">
              <Icon.check className="h-7 w-7" />
            </span>
            <div>
              <h1 className="text-xl font-bold text-content">
                Complaint submitted
              </h1>
              <p className="mt-1 text-sm text-content-muted">
                Save your tracking code to follow progress.
              </p>
            </div>

            <div className="w-full rounded-xl border border-border bg-surface-muted p-4">
              <p className="text-xs font-medium uppercase tracking-wide text-content-subtle">
                Tracking code
              </p>
              <div className="mt-1 flex items-center justify-center gap-2">
                <span className="font-mono text-2xl font-bold tracking-wider text-content">
                  {result.tracking_code}
                </span>
                <button
                  type="button"
                  onClick={() => {
                    navigator.clipboard
                      ?.writeText(result.tracking_code)
                      .then(() => setCopied(true));
                  }}
                  className="rounded-md border border-border px-2 py-1 text-xs text-content-muted hover:bg-surface"
                  aria-label="Copy tracking code"
                >
                  {copied ? "Copied" : "Copy"}
                </button>
              </div>
            </div>

            <div className="flex flex-wrap justify-center gap-3">
              <Link href={`/track?code=${result.tracking_code}`}>
                <Button>
                  <Icon.search className="h-4 w-4" />
                  Track this complaint
                </Button>
              </Link>
              <Button
                variant="secondary"
                onClick={() => {
                  setResult(null);
                  setCopied(false);
                  setTitle("");
                  setDescription("");
                  setLocation("");
                }}
              >
                Submit another
              </Button>
            </div>
          </CardBody>
        </Card>
      </Container>
    );
  }

  // ---- Form state ----
  return (
    <Container size="narrow" className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Residents"
        title="Submit a complaint"
        description="Report a non-emergency issue. You'll receive a tracking code to follow its progress."
      />

      {error && <Alert tone="error">{error}</Alert>}

      <Card>
        <CardBody>
          <form onSubmit={onSubmit} className="flex flex-col gap-5" noValidate>
            <Field label="City" htmlFor="city" required>
              <Select
                id="city"
                value={cityId}
                onChange={(e) => setCityId(Number(e.target.value))}
                required
              >
                {cities.length === 0 && <option value="">Loading…</option>}
                {cities.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </Select>
            </Field>

            <Field
              label="Title"
              htmlFor="title"
              required
              hint="A short summary — at least 3 characters."
            >
              <Input
                id="title"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                minLength={3}
                maxLength={200}
                required
                placeholder="e.g. Large pothole on Main St"
              />
            </Field>

            <Field
              label="Description"
              htmlFor="description"
              required
              hint="Describe the issue and any safety concerns — at least 10 characters."
            >
              <Textarea
                id="description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                minLength={10}
                required
                rows={4}
                placeholder="Describe what's wrong, where, and how it affects people."
              />
            </Field>

            <Field
              label="Location"
              htmlFor="location"
              hint="Optional, but helps us route and de-duplicate accurately."
            >
              <Input
                id="location"
                value={location}
                onChange={(e) => setLocation(e.target.value)}
                maxLength={300}
                placeholder="e.g. Main St & 1st Ave"
              />
            </Field>

            <div className="grid gap-5 sm:grid-cols-2">
              <Field label="Your name" htmlFor="name" hint="Optional">
                <Input
                  id="name"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  maxLength={120}
                  autoComplete="name"
                />
              </Field>
              <Field label="Email" htmlFor="email" hint="Optional">
                <Input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  autoComplete="email"
                  placeholder="you@example.com"
                />
              </Field>
            </div>

            <div className="flex items-center justify-between gap-3 border-t border-border pt-4">
              <p className="text-xs text-content-subtle">
                Your report is reviewed by city staff before any action.
              </p>
              <Button type="submit" loading={submitting}>
                {submitting ? "Submitting…" : "Submit complaint"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>
    </Container>
  );
}
