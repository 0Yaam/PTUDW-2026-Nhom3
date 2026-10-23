import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";
import { CategoryGrid } from "@/components/category-grid";
import { getCategories } from "@/lib/api/categories";
import { siteUrl } from "@/lib/site-url";

export const dynamic = "force-dynamic";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("categoryDirectory");
  return { title: t("title"), description: t("description"), alternates: { canonical: siteUrl("/categories") } };
}

export default async function CategoriesPage() {
  const [categories, t] = await Promise.all([getCategories(), getTranslations("categoryDirectory")]);
  return (
    <main id="main-content" className="category-section">
      <header className="section-heading">
        <div><p className="eyebrow">{t("eyebrow")}</p><h1>{t("title")}</h1></div>
        <p>{t("description")}</p>
      </header>
      <p className="section-footnote">{t("total", { count: categories.length })}</p>
      <CategoryGrid categories={categories} />
    </main>
  );
}
