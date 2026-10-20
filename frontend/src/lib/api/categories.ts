import type { Category } from "@/components/category-grid";
import { ApiError, apiRequest } from "@/lib/api/client";

export async function getCategories(): Promise<Category[]> {
  return apiRequest<Category[]>("/api/v1/categories", {
    // Admin edits should appear on the public category list on the next request.
    cache: "no-store",
  });
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
  try {
    return await apiRequest<CategoryDetail>(
      `/api/v1/categories/${encodeURIComponent(slug)}`,
      // Admin edits should appear on the detail page on the next request.
      { cache: "no-store" },
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
