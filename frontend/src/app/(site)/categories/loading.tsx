import { getTranslations } from "next-intl/server";
import { LoadingState } from "@/components/ui/feedback";

export default async function CategoriesLoading() {
  const t = await getTranslations("categoryDirectory");
  return <main id="main-content" className="category-section"><LoadingState label={t("loading")} /></main>;
}
