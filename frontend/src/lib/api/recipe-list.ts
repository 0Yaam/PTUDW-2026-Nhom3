export type RecipeListDifficulty = "Easy" | "Medium" | "Hard" | "Expert";
export type RecipeListSort =
  | "-createdAt"
  | "createdAt"
  | "title"
  | "-title"
  | "cookTime"
  | "-cookTime";

export type RecipeListParams = {
  q?: string;
  page: number;
  pageSize: number;
  categoryId?: string;
  difficulty?: RecipeListDifficulty;
  maxCookTime?: number;
  minServings?: number;
  sort: RecipeListSort;
};

export type RecipeListItem = {
  id: string;
  title: string;
  slug: string;
  description: string;
  category: { id: string; name: string; slug: string };
  prepTimeMinutes: number;
  cookTimeMinutes: number;
  servings: number;
  difficulty: number;
  status: "Draft" | "Published" | "Archived";
  createdAt: string;
  relevanceScore?: number;
};

export type PagedRecipeList = {
  items: RecipeListItem[];
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
};

export async function getRecipeList(
  params: RecipeListParams,
  accessToken?: string,
): Promise<PagedRecipeList> {
  const query = new URLSearchParams({
    page: String(params.page),
    pageSize: String(params.pageSize),
    sort: params.sort,
  });
  if (params.categoryId) query.set("categoryId", params.categoryId);
  if (params.difficulty) query.set("difficulty", params.difficulty);
  if (params.maxCookTime !== undefined) query.set("maxCookTime", String(params.maxCookTime));
  if (params.minServings !== undefined) query.set("minServings", String(params.minServings));
  if (params.q) query.set("q", params.q);

  const endpoint = params.q ? "recipes/search" : "recipes";
  return apiRequest<PagedRecipeList>(`/api/v1/${endpoint}?${query}`, {
    cache: "no-store",
    headers: !params.q && accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
}
import { ApiError, apiRequest } from "@/lib/api/client";

export { ApiError as RecipeListApiError };
