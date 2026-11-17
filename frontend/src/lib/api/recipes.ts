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

export type RecipeDraft = Omit<RecipeDraftInput, "nutrition"> & {
  id: string;
  slug: string;
  authorId: string;
  status: "Draft" | "Published" | "Archived";
  createdAt: string;
  rowVersion: string;
  nutrition: RecipeDetail["nutrition"];
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
  /** Read a public recipe; hide expected 404/403 responses from the detail page. */
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
  /** Create a private draft owned by the current Author or Admin. */
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
  /** Read an editable recipe, optionally sending credentials for private states. */
  return apiRequest<RecipeDetail>(`/api/v1/recipes/${encodeURIComponent(slug)}`, {
    cache: "no-store",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
}

export function updateRecipe(input: RecipeDraftInput, recipe: RecipeDetail, accessToken: string) {
  /** Save editable fields using the row version to prevent lost updates. */
  return apiRequest<RecipeDraft>(`/api/v1/recipes/${recipe.id}`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${accessToken}`, "If-Match": `"${recipe.rowVersion}"` },
    body: JSON.stringify(input),
  });
}

export type RecipeAction = "publish" | "unpublish" | "archive" | "delete";

export function changeRecipeStatus(recipeId: string, action: RecipeAction, accessToken: string) {
  /** Publish, unpublish, archive, or delete a recipe through its matching endpoint. */
  return apiRequest<RecipeDraft | void>(
    `/api/v1/recipes/${recipeId}${action === "delete" ? "" : `/${action}`}`,
    { method: action === "delete" ? "DELETE" : "PATCH", headers: { Authorization: `Bearer ${accessToken}` } },
  );
}

export type RecipeIngredientInput = { ingredientName: string; quantity: number; unit: string; orderIndex?: number };
export type RecipeStepInput = { instruction: string; durationMinutes: number | null; imageUrl: string | null; stepNumber?: number };

export function saveRecipeIngredient(recipeId: string, input: RecipeIngredientInput, accessToken: string, id?: string) {
  /** Create or update one ingredient row while preserving its order index. */
  return apiRequest<RecipeDetail["ingredients"][number]>(
    `/api/v1/recipes/${recipeId}/ingredients${id ? `/${id}` : ""}`,
    { method: id ? "PUT" : "POST", headers: { Authorization: `Bearer ${accessToken}` }, body: JSON.stringify(input) },
  );
}

export function saveRecipeStep(recipeId: string, input: RecipeStepInput, accessToken: string, id?: string) {
  /** Create or update one ordered preparation step. */
  return apiRequest<RecipeDetail["steps"][number]>(
    `/api/v1/recipes/${recipeId}/steps${id ? `/${id}` : ""}`,
    { method: id ? "PUT" : "POST", headers: { Authorization: `Bearer ${accessToken}` }, body: JSON.stringify(input) },
  );
}

export function deleteRecipeContent(recipeId: string, kind: "ingredients" | "steps", id: string, accessToken: string) {
  /** Remove one ingredient or step after the editor confirms the action. */
  return apiRequest<void>(`/api/v1/recipes/${recipeId}/${kind}/${id}`, {
    method: "DELETE", headers: { Authorization: `Bearer ${accessToken}` },
  });
}

async function sendRecipeImage(
  path: string,
  file: File,
  accessToken: string,
): Promise<RecipeImage> {
  /** Send multipart image data without forcing a JSON content type header. */
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
  /** Upload a new recipe image and return its generated metadata. */
  return sendRecipeImage(`/api/v1/recipes/${recipeId}/images`, file, accessToken);
}

export function replaceRecipeImage(
  recipeId: string,
  imageId: string,
  file: File,
  accessToken: string,
): Promise<RecipeImage> {
  /** Replace an existing image while retaining the image record identity. */
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
  /** Mark one image as primary; the backend clears the previous primary image. */
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
  /** Delete an image record and enqueue object cleanup on the backend. */
  return apiRequest<void>(`/api/v1/recipes/${recipeId}/images/${imageId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
