import type { Metadata } from "next";
import { NextIntlClientProvider } from "next-intl";
import { getLocale, getMessages } from "next-intl/server";
import { siteUrl } from "@/lib/site-url";
import "./globals.css";

export async function generateMetadata(): Promise<Metadata> {
  const locale = await getLocale();
  return {
    metadataBase: new URL(siteUrl()),
    title: { default: "Small Kitchen | Culinary Blog", template: "%s | Small Kitchen" },
    description: locale === "vi"
      ? "Khám phá danh mục món ăn, công thức và câu chuyện từ căn bếp."
      : "Explore food categories, home recipes, and stories from the kitchen.",
    alternates: { canonical: "/" },
  };
}

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  const [locale, messages] = await Promise.all([getLocale(), getMessages()]);
  return (
    <html lang={locale}>
      <body><NextIntlClientProvider messages={messages}>{children}</NextIntlClientProvider></body>
    </html>
  );
}
