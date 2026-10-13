import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { RecipeList } from "@/components/recipe-list";
import { siteUrl } from "@/lib/site-url";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("recipeList");
  return {
    title: t("title"),
    description: t("description"),
    alternates: { canonical: siteUrl("/recipes") },
  };
}

export default function RecipesPage() {
  return <RecipeList />;
}
