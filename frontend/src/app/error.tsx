"use client";

import { useTranslations } from "next-intl";
import { ErrorState } from "@/components/ui/feedback";

export default function ErrorPage({ reset }: { reset: () => void }) {
  const t = useTranslations("status");
  return (
    <main id="main-content" className="error-shell">
      <p className="eyebrow">{t("connection")}</p>
      <ErrorState title={t("title")} description={t("description")} action={{ label: t("retry"), onClick: reset }} />
    </main>
  );
}
