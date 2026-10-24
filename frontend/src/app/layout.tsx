import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CivicRoute AI",
  description:
    "Agentic AI-powered smart city complaint management platform.",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className="min-h-screen antialiased">{children}</body>
    </html>
  );
}
