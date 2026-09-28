// The Problem Details shape is the one the whole API speaks (RFC 7807), so it
// is reused rather than restated here.
import { type ProblemDetails } from "@/lib/api/recipes";

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

export class ProfileApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly problem: ProblemDetails,
  ) {
    super(problem.detail ?? "Profile request failed");
  }
}

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request(accessToken: string, init?: RequestInit): Promise<Profile> {
  const response = await fetch(`${apiUrl}/api/v1/auth/profile`, {
    ...init,
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
      ...init?.headers,
    },
    cache: "no-store",
  });

  if (!response.ok) {
    let problem: ProblemDetails = {};
    try {
      problem = (await response.json()) as ProblemDetails;
    } catch {
      problem = { detail: "The API returned an unreadable error." };
    }
    throw new ProfileApiError(response.status, problem);
  }

  return response.json() as Promise<Profile>;
}

export function getProfile(accessToken: string): Promise<Profile> {
  return request(accessToken);
}

export function updateProfile(input: ProfileInput, accessToken: string): Promise<Profile> {
  return request(accessToken, { method: "PUT", body: JSON.stringify(input) });
}
