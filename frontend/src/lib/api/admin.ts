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
