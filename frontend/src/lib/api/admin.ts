import { apiRequest } from "@/lib/api/client";

/** Kiểu dữ liệu dùng cho các endpoint `/api/v1/admin` chỉ dành cho Admin. */
export type AdminLoginResponse = {
  accessToken: string;
  refreshToken?: string;
  expiresAt?: string;
  user: { fullName: string; roles: string[] };
};

export type AdminOverview = {
  users: number;
  categories: number;
  images: number;
  recipes: { total: number; draft: number; published: number; archived: number };
  jobs: Record<"email" | "resize" | "cleanup", { pending: number; failed: number }>;
  recentRecipes: {
    id: string;
    title: string;
    status: "Draft" | "Published" | "Archived";
    author: string;
    createdAt: string;
  }[];
};

/** Lấy số liệu dashboard và hoạt động gần đây của Admin đã xác thực. */
export async function getAdminOverview(accessToken: string): Promise<AdminOverview> {
  return apiRequest<AdminOverview>("/api/v1/admin/overview", {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
}

export type AdminUser = {
  id: string;
  fullName: string;
  email: string;
  userName: string;
  role: string;
  avatarUrl?: string | null;
  createdAt: string;
};

export type PagedAdminUsers = {
  items: AdminUser[];
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
};

export type AdminUsersParams = {
  page?: number;
  pageSize?: number;
  q?: string;
  role?: string;
};

/** Lấy một trang người dùng theo bộ lọc, giữ phân trang ở phía server. */
export async function getAdminUsers(
  params: AdminUsersParams,
  accessToken: string,
): Promise<PagedAdminUsers> {
  const query = new URLSearchParams();
  if (params.page) query.set("page", String(params.page));
  if (params.pageSize) query.set("pageSize", String(params.pageSize));
  if (params.q) query.set("q", params.q);
  if (params.role) query.set("role", params.role);

  return apiRequest<PagedAdminUsers>(`/api/v1/admin/users?${query.toString()}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
}
