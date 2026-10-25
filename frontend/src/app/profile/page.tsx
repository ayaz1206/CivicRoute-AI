"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { getMe, getToken, logout, type CurrentUser } from "@/lib/api";
import { Container, PageHeader } from "@/components/ui/Page";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { Alert } from "@/components/ui/Alert";
import { Skeleton } from "@/components/ui/feedback";
import { Icon } from "@/components/ui/Icon";

function initials(user: CurrentUser): string {
  const base = user.full_name?.trim() || user.email;
  const parts = base.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase();
  return base.slice(0, 2).toUpperCase();
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between gap-4 py-3">
      <dt className="text-sm text-content-muted">{label}</dt>
      <dd className="text-sm font-medium text-content">{value}</dd>
    </div>
  );
}

export default function ProfilePage() {
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [state, setState] = useState<"loading" | "ready" | "unauth">("loading");

  useEffect(() => {
    if (getToken() == null) {
      setState("unauth");
      return;
    }
    getMe().then((u) => {
      if (u) {
        setUser(u);
        setState("ready");
      } else {
        // Token missing/expired — getMe() already cleared a stale token.
        setState("unauth");
      }
    });
  }, []);

  if (state === "loading") {
    return (
      <Container size="narrow" className="flex flex-col gap-6">
        <PageHeader eyebrow="Staff" title="My profile" />
        <Card>
          <CardBody className="flex flex-col gap-3">
            <Skeleton className="h-16 w-16 rounded-full" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-2/3" />
          </CardBody>
        </Card>
      </Container>
    );
  }

  if (state === "unauth" || !user) {
    return (
      <Container size="narrow" className="flex flex-col gap-6">
        <PageHeader eyebrow="Staff" title="My profile" />
        <Alert
          tone="warning"
          title="Your session has ended"
          action={
            <Link href="/login">
              <Button size="sm">Sign in again</Button>
            </Link>
          }
        >
          Please sign in to view your profile.
        </Alert>
      </Container>
    );
  }

  return (
    <Container size="narrow" className="flex flex-col gap-6">
      <PageHeader
        eyebrow="Staff"
        title="My profile"
        description="Your CivicRoute AI staff account."
      />

      <Card>
        <CardBody className="flex items-center gap-4">
          <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-brand-500 to-brand-700 text-lg font-semibold text-white">
            {initials(user)}
          </span>
          <div className="min-w-0">
            <p className="truncate text-lg font-semibold text-content">
              {user.full_name?.trim() || user.email.split("@")[0]}
            </p>
            <p className="truncate text-sm text-content-muted">{user.email}</p>
            <Badge tone="brand" className="mt-2 capitalize">
              <Icon.shield className="h-3 w-3" />
              {user.role}
            </Badge>
          </div>
        </CardBody>
      </Card>

      <Card>
        <CardHeader title="Account details" />
        <CardBody>
          <dl className="divide-y divide-border">
            <Row
              label="Name"
              value={user.full_name?.trim() || "—"}
            />
            <Row label="Email" value={user.email} />
            <Row label="Role" value={<span className="capitalize">{user.role}</span>} />
            <Row
              label="Status"
              value={
                <Badge tone={user.is_active ? "success" : "neutral"}>
                  {user.is_active ? "Active" : "Inactive"}
                </Badge>
              }
            />
          </dl>
        </CardBody>
      </Card>

      <div className="flex gap-3">
        <Link href="/staff">
          <Button variant="secondary">
            <Icon.inbox className="h-4 w-4" />
            Staff dashboard
          </Button>
        </Link>
        <Button
          variant="ghost"
          onClick={() => {
            logout();
            router.push("/");
            router.refresh();
          }}
        >
          <Icon.logout className="h-4 w-4" />
          Sign out
        </Button>
      </div>
    </Container>
  );
}
