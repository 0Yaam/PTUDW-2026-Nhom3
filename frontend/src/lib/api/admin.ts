import { apiRequest } from "@/lib/api/client";

/** Contracts for the Admin-only `/api/v1/admin` endpoints. */
export type AdminLoginResponse = {
  accessToken: string;
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
  role: "Admin" | "Author";
  createdAt: string;
};

export type AdminUserPage = {
  items: AdminUser[];
  totalCount: number;
  page: number;
  pageSize: number;
  totalPages: number;
  hasNextPage: boolean;
  hasPreviousPage: boolean;
};

export async function getAdminUsers(
  accessToken: string,
  options: { page?: number; pageSize?: number; q?: string; role?: "Admin" | "Author" } = {},
): Promise<AdminUserPage> {
  const params = new URLSearchParams({
    page: String(options.page ?? 1),
    pageSize: String(options.pageSize ?? 20),
  });
  if (options.q?.trim()) params.set("q", options.q.trim());
  if (options.role) params.set("role", options.role);
  return apiRequest<AdminUserPage>(`/api/v1/admin/users?${params.toString()}`, {
    headers: { Authorization: `Bearer ${accessToken}` },
    cache: "no-store",
  });
}
