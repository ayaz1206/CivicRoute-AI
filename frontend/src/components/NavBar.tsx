import Link from "next/link";
import { AuthLink } from "./AuthLink";

export function NavBar() {
  return (
    <nav className="border-b">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
        <Link href="/" className="font-bold tracking-tight">
          CivicRoute AI
        </Link>
        <div className="flex gap-4 text-sm">
          <Link href="/submit" className="hover:underline">
            Submit
          </Link>
          <Link href="/track" className="hover:underline">
            Track
          </Link>
          <Link href="/staff" className="hover:underline">
            Staff
          </Link>
          <Link href="/review" className="hover:underline">
            AI Review
          </Link>
          <Link href="/analytics" className="hover:underline">
            Analytics
          </Link>
          <AuthLink />
        </div>
      </div>
    </nav>
  );
}
