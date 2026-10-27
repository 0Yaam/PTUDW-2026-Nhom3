import { ApiError, apiBaseUrl, apiRequest, readProblemDetails } from "@/lib/api/client";

export { ApiError as RecipeApiError };
export type { ProblemDetails } from "@/lib/api/client";

export type RecipeDraftInput = {
  title: string;
  description: string;
  categoryId: string;
  prepTimeMinutes: number;
  cookTimeMinutes: number;
  servings: number;
  difficulty: number;
  instructions: string;
  nutrition?: {
    calories?: number;
    protein?: number;
    carbohydrates?: number;
    fat?: number;
    fiber?: number;
    sodium?: number;
  };
};

export type RecipeDraft = RecipeDraftInput & {
  id: string;
  slug: string;
  authorId: string;
  status: "Draft";
  createdAt: string;
};

export type RecipeDetail = Omit<RecipeDraftInput, "nutrition"> & {
  id: string;
  slug: string;
  authorId: string;
  status: "Draft" | "Published" | "Archived";
  createdAt: string;
  publishedAt: string | null;
  rowVersion: string;
  nutrition: {
    calories: number | null;
    protein: number | null;
    carbohydrates: number | null;
    fat: number | null;
    fiber: number | null;
    sodium: number | null;
  } | null;
  category: { id: string; name: string; slug: string };
  author: { id: string; fullName: string; userName: string };
  ingredients: {
    id: string; ingredientId: string; name: string; quantity: number;
    unit: string; orderIndex: number;
  }[];
  steps: {
    id: string; recipeId: string; stepNumber: number; instruction: string;
    durationMinutes: number | null; imageUrl: string | null;
  }[];
  images: {
    id: string; recipeId: string; originalUrl: string; mediumUrl: string | null;
    thumbnailUrl: string | null; altText: string | null;
    isPrimary: boolean; orderIndex: number;
  }[];
};

export type RecipeImage = RecipeDetail["images"][number];

export async function getRecipe(slug: string): Promise<RecipeDetail | null> {
  try {
    return await apiRequest<RecipeDetail>(`/api/v1/recipes/${encodeURIComponent(slug)}`, {
      cache: "no-store",
    });
  } catch (error) {
    if (error instanceof ApiError && (error.status === 404 || error.status === 403)) return null;
    throw error;
  }
}

export type PublishedRecipeLink = { slug: string; createdAt: string };

/** Walks the public, paginated recipe list to collect every published slug for the sitemap. */
export async function listPublishedRecipes(): Promise<PublishedRecipeLink[]> {
  const items: PublishedRecipeLink[] = [];
  let page = 1;
  let hasNextPage = true;
  while (hasNextPage) {
    const body = await apiRequest<{
      items: { slug: string; createdAt: string }[];
      hasNextPage: boolean;
    }>(`/api/v1/recipes?page=${page}&pageSize=50`, {
      cache: "no-store",
    });
    items.push(...body.items.map(({ slug, createdAt }) => ({ slug, createdAt })));
    hasNextPage = body.hasNextPage;
    page += 1;
  }
  return items;
}

export async function createRecipeDraft(
  input: RecipeDraftInput,
  accessToken: string,
): Promise<RecipeDraft> {
  return apiRequest<RecipeDraft>("/api/v1/recipes", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
    },
    body: JSON.stringify(input),
  });
}

export async function getRecipeDetail(
  slug: string,
  accessToken?: string,
): Promise<RecipeDetail> {
  return apiRequest<RecipeDetail>(`/api/v1/recipes/${encodeURIComponent(slug)}`, {
    cache: "no-store",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
}

async function sendRecipeImage(
  path: string,
  file: File,
  accessToken: string,
): Promise<RecipeImage> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    method: "POST",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: form,
  });
  if (!response.ok) throw new ApiError(response.status, await readProblemDetails(response));
  return (await response.json()) as RecipeImage;
}

export function uploadRecipeImage(
  recipeId: string,
  file: File,
  accessToken: string,
): Promise<RecipeImage> {
  return sendRecipeImage(`/api/v1/recipes/${recipeId}/images`, file, accessToken);
}

export function replaceRecipeImage(
  recipeId: string,
  imageId: string,
  file: File,
  accessToken: string,
): Promise<RecipeImage> {
  return sendRecipeImage(
    `/api/v1/recipes/${recipeId}/images/${imageId}/replace`,
    file,
    accessToken,
  );
}

export function setPrimaryRecipeImage(
  recipeId: string,
  imageId: string,
  accessToken: string,
): Promise<RecipeImage> {
  return apiRequest<RecipeImage>(`/api/v1/recipes/${recipeId}/images/${imageId}`, {
    method: "PATCH",
    headers: { Authorization: `Bearer ${accessToken}` },
    body: JSON.stringify({ isPrimary: true }),
  });
}

export function deleteRecipeImage(
  recipeId: string,
  imageId: string,
  accessToken: string,
): Promise<void> {
  return apiRequest<void>(`/api/v1/recipes/${recipeId}/images/${imageId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
