import type { Category } from "@/components/category-grid";
import { ApiError, apiRequest } from "@/lib/api/client";

/** Lấy danh sách danh mục công khai và không dùng dữ liệu cũ sau khi Admin sửa. */
export async function getCategories(): Promise<Category[]> {
  return apiRequest<Category[]>("/api/v1/categories", {
    // Thay đổi của Admin phải xuất hiện ở danh sách công khai từ request kế tiếp.
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

/** Trả null khi slug không tồn tại để trang tự hiển thị trạng thái không tìm thấy. */
export async function getCategory(slug: string): Promise<CategoryDetail | null> {
  try {
    return await apiRequest<CategoryDetail>(
      `/api/v1/categories/${encodeURIComponent(slug)}`,
      // Thay đổi của Admin phải xuất hiện ở trang chi tiết từ request kế tiếp.
      { cache: "no-store" },
    );
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
