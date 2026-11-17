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
  /** Đọc công thức công khai; ẩn lỗi 404/403 dự kiến khỏi trang chi tiết. */
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

/** Duyệt danh sách công thức phân trang để gom toàn bộ slug đã đăng cho sitemap. */
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
  /** Tạo bản nháp riêng thuộc về Author hoặc Admin hiện tại. */
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
  /** Đọc công thức có thể sửa, tùy chọn gửi token cho trạng thái riêng tư. */
  return apiRequest<RecipeDetail>(`/api/v1/recipes/${encodeURIComponent(slug)}`, {
    cache: "no-store",
    headers: accessToken ? { Authorization: `Bearer ${accessToken}` } : undefined,
  });
}

export function updateRecipe(input: RecipeDraftInput, recipe: RecipeDetail, accessToken: string) {
  /** Lưu trường chỉnh sửa kèm row version để tránh ghi đè thay đổi. */
  return apiRequest<RecipeDraft>(`/api/v1/recipes/${recipe.id}`, {
    method: "PUT",
    headers: { Authorization: `Bearer ${accessToken}`, "If-Match": `"${recipe.rowVersion}"` },
    body: JSON.stringify(input),
  });
}

export type RecipeAction = "publish" | "unpublish" | "archive" | "delete";

export function changeRecipeStatus(recipeId: string, action: RecipeAction, accessToken: string) {
  /** Đăng, gỡ đăng, lưu trữ hoặc xóa công thức qua endpoint tương ứng. */
  return apiRequest<RecipeDraft | void>(
    `/api/v1/recipes/${recipeId}${action === "delete" ? "" : `/${action}`}`,
    { method: action === "delete" ? "DELETE" : "PATCH", headers: { Authorization: `Bearer ${accessToken}` } },
  );
}

export type RecipeIngredientInput = { ingredientName: string; quantity: number; unit: string; orderIndex?: number };
export type RecipeStepInput = { instruction: string; durationMinutes: number | null; imageUrl: string | null; stepNumber?: number };

export function saveRecipeIngredient(recipeId: string, input: RecipeIngredientInput, accessToken: string, id?: string) {
  /** Tạo hoặc cập nhật một nguyên liệu và giữ nguyên thứ tự hiển thị. */
  return apiRequest<RecipeDetail["ingredients"][number]>(
    `/api/v1/recipes/${recipeId}/ingredients${id ? `/${id}` : ""}`,
    { method: id ? "PUT" : "POST", headers: { Authorization: `Bearer ${accessToken}` }, body: JSON.stringify(input) },
  );
}

export function saveRecipeStep(recipeId: string, input: RecipeStepInput, accessToken: string, id?: string) {
  /** Tạo hoặc cập nhật một bước nấu theo thứ tự. */
  return apiRequest<RecipeDetail["steps"][number]>(
    `/api/v1/recipes/${recipeId}/steps${id ? `/${id}` : ""}`,
    { method: id ? "PUT" : "POST", headers: { Authorization: `Bearer ${accessToken}` }, body: JSON.stringify(input) },
  );
}

export function deleteRecipeContent(recipeId: string, kind: "ingredients" | "steps", id: string, accessToken: string) {
  /** Xóa một nguyên liệu hoặc bước nấu sau khi trình chỉnh sửa xác nhận. */
  return apiRequest<void>(`/api/v1/recipes/${recipeId}/${kind}/${id}`, {
    method: "DELETE", headers: { Authorization: `Bearer ${accessToken}` },
  });
}

async function sendRecipeImage(
  path: string,
  file: File,
  accessToken: string,
): Promise<RecipeImage> {
  /** Gửi dữ liệu ảnh multipart mà không ép header Content-Type JSON. */
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
  /** Tải ảnh mới lên và trả về metadata do server tạo. */
  return sendRecipeImage(`/api/v1/recipes/${recipeId}/images`, file, accessToken);
}

export function replaceRecipeImage(
  recipeId: string,
  imageId: string,
  file: File,
  accessToken: string,
): Promise<RecipeImage> {
  /** Thay ảnh hiện có nhưng giữ nguyên danh tính bản ghi ảnh. */
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
  /** Đặt một ảnh làm ảnh chính; backend sẽ bỏ ảnh chính trước đó. */
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
  /** Xóa bản ghi ảnh và xếp tác vụ dọn object ở backend. */
  return apiRequest<void>(`/api/v1/recipes/${recipeId}/images/${imageId}`, {
    method: "DELETE",
    headers: { Authorization: `Bearer ${accessToken}` },
  });
}
