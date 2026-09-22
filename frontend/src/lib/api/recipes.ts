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

export type ProblemDetails = {
  type?: string;
  title?: string;
  status?: number;
  detail?: string;
  errors?: Record<string, string[]>;
};

export class RecipeApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly problem: ProblemDetails,
  ) {
    super(problem.detail ?? "Recipe request failed");
  }
}

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export async function createRecipeDraft(
  input: RecipeDraftInput,
  accessToken: string,
): Promise<RecipeDraft> {
  const response = await fetch(`${apiUrl}/api/v1/recipes`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${accessToken}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify(input),
  });

  if (!response.ok) {
    let problem: ProblemDetails = {};
    try {
      problem = (await response.json()) as ProblemDetails;
    } catch {
      problem = { detail: "The API returned an unreadable error." };
    }
    throw new RecipeApiError(response.status, problem);
  }

  return response.json() as Promise<RecipeDraft>;
}
