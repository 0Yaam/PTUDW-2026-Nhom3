import { SiteFooter } from "@/components/site-footer";
import { SiteHeader } from "@/components/site-header";
import { SiteAccessProvider } from "@/components/site-account-controls";

export default function SiteLayout({ children }: { children: React.ReactNode }) {
  return <SiteAccessProvider><SiteHeader />{children}<SiteFooter /></SiteAccessProvider>;
}
