import { cookies } from "next/headers";
import { getRequestConfig } from "next-intl/server";

export type AppLocale = "en" | "vi";

export default getRequestConfig(async () => {
  const selected = (await cookies()).get("NEXT_LOCALE")?.value;
  const locale: AppLocale = selected === "vi" ? "vi" : "en";

  return {
    locale,
    messages: (await import(`../../messages/${locale}.json`)).default,
  };
});
