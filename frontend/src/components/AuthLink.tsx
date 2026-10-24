"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { getToken, logout } from "@/lib/api";

export function AuthLink() {
  const router = useRouter();
  const [signedIn, setSignedIn] = useState(false);

  useEffect(() => {
    setSignedIn(getToken() != null);
  }, []);

  if (signedIn) {
    return (
      <button
        onClick={() => {
          logout();
          setSignedIn(false);
          router.push("/");
          router.refresh();
        }}
        className="hover:underline"
      >
        Sign out
      </button>
    );
  }
  return (
    <Link href="/login" className="hover:underline">
      Staff sign in
    </Link>
  );
}
