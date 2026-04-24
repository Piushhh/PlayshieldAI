"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { LogOut, Settings, Shield } from "lucide-react";
import { api } from "@/lib/api";

const NAV_ITEMS = [
  { href: "/dashboard", label: "Dashboard" },
  { href: "/assets", label: "Registry" },
  { href: "/cases", label: "Reports" },
  { href: "/settings", label: "Settings", icon: Settings },
];

export default function Sidebar() {
  const pathname = usePathname();
  const [unreadCount, setUnreadCount] = useState(0);
  const [userEmail, setUserEmail] = useState("");

  useEffect(() => {
    const fetchCount = () => {
      api
        .getUnreadCount()
        .then((res) => setUnreadCount(res.unread_count))
        .catch(() => {});
    };

    api
      .getMe()
      .then((user) => setUserEmail(user.email))
      .catch(() => {});

    fetchCount();
    const interval = setInterval(fetchCount, 30000);
    return () => clearInterval(interval);
  }, []);

  const handleLogout = () => {
    api.clearTokens();
    window.location.href = "/login";
  };

  return (
    <header className="sidebar">
      <div className="mx-auto flex w-[min(1480px,calc(100vw-2rem))] flex-col gap-4 py-4 md:flex-row md:items-center md:justify-between">
        <div className="flex items-center justify-between gap-4">
          <Link href="/dashboard" className="flex items-center gap-4">
            <div className="flex h-11 w-11 items-center justify-center border border-[var(--color-line)] bg-[rgba(255,255,255,0.62)]">
              <Shield size={18} />
            </div>
            <div>
              <p className="panel-kicker">PlayShield AI</p>
              <h1 className="text-xl font-bold uppercase tracking-[-0.06em]">AssetGuard</h1>
            </div>
          </Link>

          {userEmail ? (
            <div className="hidden border border-[var(--color-line)] bg-[rgba(255,255,255,0.55)] px-3 py-2 font-['IBM_Plex_Mono'] text-[0.72rem] uppercase tracking-[0.16em] text-[var(--color-ink-faint)] md:block">
              {userEmail}
            </div>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-2 md:justify-end">
          <nav className="flex flex-wrap items-center gap-2">
            {NAV_ITEMS.map((item) => {
              const isActive = pathname?.startsWith(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`sidebar-link ${isActive ? "active" : ""}`}
                >
                  {item.label}
                  {item.href === "/cases" && unreadCount > 0 ? (
                    <span className="inline-flex h-5 min-w-5 items-center justify-center border border-[var(--color-line)] bg-[var(--color-warning-bg)] px-1 text-[0.65rem] tracking-normal text-[var(--color-ink)]">
                      {unreadCount > 9 ? "9+" : unreadCount}
                    </span>
                  ) : null}
                </Link>
              );
            })}
          </nav>

          <button onClick={handleLogout} className="sidebar-link">
            <LogOut size={14} />
            Sign Out
          </button>
        </div>

        {userEmail ? (
          <div className="border border-[var(--color-line)] bg-[rgba(255,255,255,0.55)] px-3 py-2 font-['IBM_Plex_Mono'] text-[0.72rem] uppercase tracking-[0.16em] text-[var(--color-ink-faint)] md:hidden">
            {userEmail}
          </div>
        ) : null}
      </div>
    </header>
  );
}
