"use client";

import { useTranslations } from "next-intl";
import { ErrorState } from "@/components/ui/feedback";

export default function CategoriesError() {
  const t = useTranslations("categoryDirectory");
  // Reload the server-rendered list as well as the client error boundary.
  return <main id="main-content" className="category-section"><h1>{t("title")}</h1><ErrorState title={t("errorTitle")} description={t("errorDescription")} action={{ label: t("retry"), onClick: () => window.location.reload() }} /></main>;
}
