"use client";

import Link from "next/link";
import { createContext, type ReactNode, useContext, useEffect, useState } from "react";
import { getProfile } from "@/lib/api/profile";
import type { AuthSession } from "@/lib/auth-session";
import { useAuthStore } from "@/lib/auth-store";

const SiteAccess = createContext<"guest" | "admin" | null>(null);

export function SiteAccessProvider({ children }: { children: ReactNode }) {
  const session = useAuthStore();
  const [adminSession, setAdminSession] = useState<AuthSession | null>(null);

  useEffect(() => {
    if (!session) return;

    let active = true;
    void getProfile(session.accessToken)
      .then(({ roles }) => {
        if (active) setAdminSession(roles.includes("Admin") ? session : null);
      })
      .catch(() => {
        if (active) setAdminSession(null);
      });

    return () => { active = false; };
  }, [session]);

  const access = session === null ? "guest" : session === adminSession ? "admin" : null;

  return <SiteAccess.Provider value={access}>{children}</SiteAccess.Provider>;
}

export function SiteGuestBadge({ children, className }: { children: ReactNode; className: string }) {
  return useContext(SiteAccess) === "guest" ? <span className={className}>{children}</span> : null;
}

export function AdminCategoriesLink({ children, className }: { children: ReactNode; className?: string }) {
  if (useContext(SiteAccess) !== "admin") return null;

  return <Link className={className} href="/admin/categories">{children}</Link>;
}
