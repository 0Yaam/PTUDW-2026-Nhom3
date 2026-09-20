import Link from "next/link";
import { MobileNav } from "@/components/mobile-nav";

const links = [
  { href: "/#categories", label: "Categories" },
  { href: "/#about", label: "Our story" },
  { href: "/#auth", label: "Account" },
];

export function SiteHeader() {
  return (
    <>
      <a className="skip-link" href="#main-content">Skip to content</a>
      <header className="site-header"><div className="site-header-inner">
        <Link className="site-brand" href="/" aria-label="Small Kitchen home"><span className="site-brand-mark" aria-hidden="true">✳</span><span className="site-brand-name">small<span>kitchen</span><small>Food stories & recipes</small></span></Link>
        <nav className="desktop-nav" aria-label="Main navigation">{links.map((link) => <a href={link.href} key={link.href}>{link.label}</a>)}</nav>
        <Link className="header-action" href="/admin/categories">Manage categories <span aria-hidden="true">↗</span></Link>
        <MobileNav links={links} />
      </div></header>
    </>
  );
}
