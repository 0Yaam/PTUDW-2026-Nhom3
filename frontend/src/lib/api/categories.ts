import type { Category } from "@/components/category-grid";

const apiUrl =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

export async function getCategories(): Promise<Category[]> {
  const response = await fetch(`${apiUrl}/api/v1/categories`, {
    // Admin edits should appear on the public category list on the next request.
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Categories API returned ${response.status}`);
  }

  return response.json() as Promise<Category[]>;
}

export type RecipeCard = {
  id: string;
  title: string;
  slug: string;
  description: string;
  prep_time_minutes: number;
  cook_time_minutes: number;
  servings: number;
  difficulty: number;
};

export type CategoryDetail = Category & { recipes: RecipeCard[] };

/** Returns null when no category owns the slug, so the page can show its own not-found state. */
export async function getCategory(slug: string): Promise<CategoryDetail | null> {
  const response = await fetch(
    `${apiUrl}/api/v1/categories/${encodeURIComponent(slug)}`,
    // Admin edits should appear on the detail page on the next request.
    { cache: "no-store" },
  );

  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Category API returned ${response.status}`);
  }

  return response.json() as Promise<CategoryDetail>;
}
