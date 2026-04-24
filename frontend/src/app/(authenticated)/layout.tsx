"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/Sidebar";
import { api } from "@/lib/api";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const router = useRouter();
  const [mounted, setMounted] = useState(false);
  const authenticated = api.isAuthenticated();

  useEffect(() => {
    setMounted(true);
    if (!authenticated) {
      router.push("/login");
    }
  }, [authenticated, router]);

  // On the server or during first hydration, always render the loading state
  // to avoid structural mismatches with the authenticated client render.
  if (!mounted || !authenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[var(--color-bg)]">
        <div className="pulse-glow flex h-14 w-14 items-center justify-center border border-[var(--color-line)] bg-[var(--color-panel)] font-['IBM_Plex_Mono'] text-sm uppercase tracking-[0.2em]">
          AI
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-[var(--color-bg)]">
      <Sidebar />
      <main className="main-content">{children}</main>
    </div>
  );
}
