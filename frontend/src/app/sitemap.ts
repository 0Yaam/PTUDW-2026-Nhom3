import type { MetadataRoute } from "next";

import { getCategories } from "@/lib/api/categories";
import { listPublishedRecipes } from "@/lib/api/recipes";
import { siteUrl } from "@/lib/site-url";

export default async function sitemap(): Promise<MetadataRoute.Sitemap> {
  const [categories, recipes] = await Promise.all([getCategories(), listPublishedRecipes()]);

  return [
    { url: siteUrl("/"), changeFrequency: "weekly", priority: 1 },
    ...categories.map((category) => ({
      url: siteUrl(`/categories/${category.slug}`),
      changeFrequency: "weekly" as const,
      priority: 0.7,
    })),
    ...recipes.map((recipe) => ({
      url: siteUrl(`/recipes/${recipe.slug}`),
      lastModified: recipe.createdAt,
      changeFrequency: "weekly" as const,
      priority: 0.8,
    })),
  ];
}
