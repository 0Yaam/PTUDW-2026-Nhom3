import type { Category } from "@/components/category-grid";

const apiUrl =
  process.env.API_INTERNAL_URL ??
  process.env.NEXT_PUBLIC_API_URL ??
  "http://localhost:8000";

export async function getCategories(): Promise<Category[]> {
  const response = await fetch(`${apiUrl}/api/v1/categories`, {
    next: { revalidate: 3600, tags: ["categories"] },
  });

  if (!response.ok) {
    throw new Error(`Categories API returned ${response.status}`);
  }

  return response.json() as Promise<Category[]>;
}

export type RecipeSummary = {
  id: string;
  title: string;
  slug: string;
  image_url: string | null;
  cook_time_minutes: number | null;
  difficulty: string | null;
};

export type CategoryDetail = Category & { recipes: RecipeSummary[] };

export async function getCategory(slug: string): Promise<CategoryDetail | null> {
  const response = await fetch(`${apiUrl}/api/v1/categories/${encodeURIComponent(slug)}`, {
    next: { revalidate: 3600, tags: ["categories"] },
  });

  if (response.status === 404) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Category API returned ${response.status}`);
  }

  return response.json() as Promise<CategoryDetail>;
}
