"use client";

import { useTranslations } from "next-intl";

export default function ErrorPage({ reset }: { reset: () => void }) {
  const t = useTranslations("status");
  return (
    <main id="main-content" className="error-shell">
      <p className="eyebrow">{t("connection")}</p>
      <h1>{t("title")}</h1>
      <p>{t("description")}</p>
      <button type="button" onClick={reset}>{t("retry")}</button>
    </main>
  );
}
