"use client";

import { useEffect, useRef } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTranslations } from "next-intl";

type NavLink = { href: string; label: string };

export function MobileNav({ links }: { links: NavLink[] }) {
  const t = useTranslations("nav");
  const details = useRef<HTMLDetailsElement>(null);
  const pathname = usePathname();

  useEffect(() => {
    details.current?.removeAttribute("open");
  }, [pathname]);

  return (
    <details className="mobile-nav" ref={details}>
      <summary aria-label={t("menu")}>{t("menu")} <span aria-hidden="true">☰</span></summary>
      <nav aria-label={t("mobile")} onClick={() => details.current?.removeAttribute("open")}>
        {links.map((link) => <a href={link.href} key={link.href}>{link.label}</a>)}
        <Link href="/admin/categories">{t("manage")}</Link>
      </nav>
    </details>
  );
}
