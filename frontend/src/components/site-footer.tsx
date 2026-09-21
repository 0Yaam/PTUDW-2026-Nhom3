import Link from "next/link";
import { useTranslations } from "next-intl";

export function SiteFooter() {
  const t = useTranslations("nav");
  const site = useTranslations("site");
  const sectionLinks = [
    { href: "/#categories", label: t("categories") },
    { href: "/#about", label: t("story") },
    { href: "/#auth", label: t("account") },
  ];
  return (
    <footer className="site-footer"><div className="site-footer-inner">
      <div><p className="footer-kicker">{site("journal")}</p><h2>{site("footerLine1")}<br /><span>{site("footerLine2")}</span></h2><p>{site("footerDescription")}</p></div>
      <nav aria-label="Footer navigation"><Link href="/">{t("home")}</Link>{sectionLinks.map((link) => <a href={link.href} key={link.href}>{link.label}</a>)}<Link href="/admin/categories">{t("admin")}</Link></nav>
    </div><div className="footer-bottom"><span>© {new Date().getFullYear()} Small Kitchen · Team 3</span><span>{site("footerMotto")}</span></div></footer>
  );
}
