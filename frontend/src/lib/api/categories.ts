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
