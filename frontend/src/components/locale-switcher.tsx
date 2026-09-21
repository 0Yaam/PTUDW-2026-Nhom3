"use client";

import { useLocale, useTranslations } from "next-intl";
import { useRouter } from "next/navigation";

export function LocaleSwitcher({ compact = false }: { compact?: boolean }) {
  const locale = useLocale();
  const t = useTranslations("language");
  const router = useRouter();

  function select(nextLocale: "en" | "vi") {
    if (nextLocale === locale) return;
    document.cookie = `NEXT_LOCALE=${nextLocale}; Path=/; Max-Age=31536000; SameSite=Lax`;
    router.refresh();
  }

  return (
    <div className={`locale-switcher${compact ? " compact" : ""}`} role="group" aria-label={t("choose")}>
      <button type="button" lang="vi" aria-pressed={locale === "vi"} onClick={() => select("vi")}>VI</button>
      <button type="button" lang="en" aria-pressed={locale === "en"} onClick={() => select("en")}>EN</button>
    </div>
  );
}
