"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { MobileNav } from "@/components/mobile-nav";
import { LocaleSwitcher } from "@/components/locale-switcher";
import { clearAuthSession } from "@/lib/auth-session";
import { apiRequest } from "@/lib/api/client";
import { useAuthStore } from "@/lib/auth-store";

export function SiteHeader() {
  const t = useTranslations("nav");
  const site = useTranslations("site");
  const authT = useTranslations("auth");
  const session = useAuthStore();
  const user = session?.user ?? null;
  const links = [
    { href: "/categories", label: t("categories") },
    { href: "/recipes", label: t("recipes") },
    { href: "/recipes/new", label: t("createRecipe") },
    { href: "/#about", label: t("story") },
    { href: "/profile", label: t("profile") },
    { href: "/change-password", label: t("security") },
    ...(!user ? [{ href: "/#auth", label: t("account") }] : []),
  ];

  async function signOut() {
    if (!session) return;
    try {
      await apiRequest<void>("/api/v1/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${session.accessToken}` },
        body: JSON.stringify({ refreshToken: session.refreshToken }),
      });
    } finally {
      clearAuthSession();
    }
  }
  return (
    <>
      <a className="skip-link" href="#main-content">{t("skip")}</a>
      <header className="site-header"><div className="site-header-inner">
        <Link className="site-brand" href="/" aria-label={t("brandHome")}><span className="site-brand-mark" aria-hidden="true">✳</span><span className="site-brand-name">small<span>kitchen</span><small>{site("tagline")}</small></span></Link>
        <nav className="desktop-nav" aria-label={t("main")}>{links.map((link) => <Link href={link.href} key={link.href}>{link.label}</Link>)}</nav>
        <LocaleSwitcher compact />
        {user && <details className="user-menu">
          <summary aria-label={t("userMenu", { name: user.fullName })}>
            <span className="user-menu-icon" aria-hidden="true"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"><circle cx="12" cy="8" r="3.5" /><path d="M4.5 20c.8-3.5 3.2-5.3 7.5-5.3s6.7 1.8 7.5 5.3" /></svg></span>
            <span className="user-menu-name">{user.fullName}</span><span className="user-menu-chevron" aria-hidden="true">⌄</span>
          </summary>
          <div className="user-menu-popover"><strong>{user.fullName}</strong><small>{user.roles.join(" · ")}</small><Link href="/profile">{t("profile")}</Link><Link href="/recipes/new">{t("createRecipe")}</Link><button type="button" onClick={() => void signOut()}>{authT("signOut")}</button></div>
        </details>}
        <Link className="header-action" href="/admin/categories">{t("manage")} <span aria-hidden="true">↗</span></Link>
        <MobileNav links={links} />
      </div></header>
    </>
  );
}
