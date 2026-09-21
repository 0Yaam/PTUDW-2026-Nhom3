import Link from "next/link";
import { useTranslations } from "next-intl";
import { MobileNav } from "@/components/mobile-nav";
import { LocaleSwitcher } from "@/components/locale-switcher";

export function SiteHeader() {
  const t = useTranslations("nav");
  const site = useTranslations("site");
  const links = [
    { href: "/#categories", label: t("categories") },
    { href: "/#about", label: t("story") },
    { href: "/#auth", label: t("account") },
  ];
  return (
    <>
      <a className="skip-link" href="#main-content">{t("skip")}</a>
      <header className="site-header"><div className="site-header-inner">
        <Link className="site-brand" href="/" aria-label="Small Kitchen home"><span className="site-brand-mark" aria-hidden="true">✳</span><span className="site-brand-name">small<span>kitchen</span><small>{site("tagline")}</small></span></Link>
        <nav className="desktop-nav" aria-label={t("main")}>{links.map((link) => <a href={link.href} key={link.href}>{link.label}</a>)}</nav>
        <LocaleSwitcher compact />
        <Link className="header-action" href="/admin/categories">{t("manage")} <span aria-hidden="true">↗</span></Link>
        <MobileNav links={links} />
      </div></header>
    </>
  );
}
