import { ApiError, apiRequest } from "@/lib/api/client";

export { ApiError as ProfileApiError };

export type Profile = {
  id: string;
  fullName: string;
  email: string;
  userName: string;
  avatarUrl: string | null;
  roles: string[];
};

export type ProfileInput = {
  fullName: string;
  userName: string;
  avatarUrl: string | null;
};

async function request(accessToken: string, init?: RequestInit): Promise<Profile> {
  return apiRequest<Profile>("/api/v1/auth/profile", {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      ...init?.headers,
    },
    cache: "no-store",
  });
}

export function getProfile(accessToken: string): Promise<Profile> {
  return request(accessToken);
}

export function updateProfile(input: ProfileInput, accessToken: string): Promise<Profile> {
  return request(accessToken, { method: "PUT", body: JSON.stringify(input) });
}
