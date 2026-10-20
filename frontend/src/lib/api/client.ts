export type ProblemDetails = {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  errors?: Record<string, string[]>;
};

export class ApiError extends Error {
  constructor(public readonly status: number, public readonly problem: ProblemDetails = {}) {
    super(problem.detail ?? problem.title ?? `Request failed with status ${status}`);
    this.name = "ApiError";
  }
}

const browserApiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const serverApiUrl = process.env.API_INTERNAL_URL ?? browserApiUrl;

export function apiBaseUrl(): string {
  return typeof window === "undefined" ? serverApiUrl : browserApiUrl;
}

export async function readProblemDetails(response: Response): Promise<ProblemDetails> {
  try {
    const problem = (await response.json()) as ProblemDetails;
    return { ...problem, status: problem.status ?? response.status };
  } catch {
    return {
      status: response.status,
      title: response.statusText || undefined,
      detail: "The API returned an unreadable error.",
    };
  }
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const response = await fetch(`${apiBaseUrl()}${path}`, { ...init, headers });
  if (!response.ok) {
    throw new ApiError(response.status, await readProblemDetails(response));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}
