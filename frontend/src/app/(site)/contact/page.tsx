import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { ContactForm } from "@/components/contact-form";
import { siteUrl } from "@/lib/site-url";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("contact");
  return {
    title: t("title"),
    description: t("description"),
    alternates: { canonical: siteUrl("/contact") },
  };
}

export default function ContactPage() {
  return <ContactForm />;
}
