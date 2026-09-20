import Link from "next/link";

const sectionLinks = [
  { href: "/#categories", label: "Categories" },
  { href: "/#about", label: "Our story" },
  { href: "/#auth", label: "Account" },
];

export function SiteFooter() {
  return (
    <footer className="site-footer"><div className="site-footer-inner">
      <div><p className="footer-kicker">The culinary journal</p><h2>LET&apos;S MAKE<br /><span>SOMETHING GOOD.</span></h2><p>Good food tastes even better together.</p></div>
      <nav aria-label="Footer navigation"><Link href="/">Home</Link>{sectionLinks.map((link) => <a href={link.href} key={link.href}>{link.label}</a>)}<Link href="/admin/categories">Admin</Link></nav>
    </div><div className="footer-bottom"><span>© {new Date().getFullYear()} Small Kitchen · Team 3</span><span>Cook. Share. Remember.</span></div></footer>
  );
}
