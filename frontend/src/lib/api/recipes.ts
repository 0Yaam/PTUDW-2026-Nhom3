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

const serverApiUrl =
  process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export type RecipeIngredient = {
  id: string;
  name: string;
  quantity: number;
  unit: string;
  orderIndex: number;
};

export type RecipeStep = {
  id: string;
  stepNumber: number;
  instruction: string;
  durationMinutes: number | null;
};

export type RecipeDetail = {
  id: string;
  title: string;
  slug: string;
  description: string;
  instructions: string;
  category: { id: string; name: string; slug: string };
  author: { id: string; fullName: string; userName: string };
  prepTimeMinutes: number;
  cookTimeMinutes: number;
  servings: number;
  difficulty: number;
  status: "Draft" | "Published" | "Archived";
  nutrition: {
    calories?: number;
    protein?: number;
    carbohydrates?: number;
    fat?: number;
    fiber?: number;
    sodium?: number;
  } | null;
  ingredients: RecipeIngredient[];
  steps: RecipeStep[];
  createdAt: string;
};

/**
 * Returns null for a missing or private recipe (404/403): the public detail page only
 * ever renders the published view, so both cases share the same not-found state.
 */
export async function getRecipe(slug: string): Promise<RecipeDetail | null> {
  const response = await fetch(`${serverApiUrl}/api/v1/recipes/${encodeURIComponent(slug)}`, {
    cache: "no-store",
  });

  if (response.status === 404 || response.status === 403) {
    return null;
  }
  if (!response.ok) {
    throw new Error(`Recipe API returned ${response.status}`);
  }

  return response.json() as Promise<RecipeDetail>;
}

export type PublishedRecipeLink = { slug: string; createdAt: string };

/** Walks the public, paginated recipe list to collect every published slug for the sitemap. */
export async function listPublishedRecipes(): Promise<PublishedRecipeLink[]> {
  const items: PublishedRecipeLink[] = [];
  let page = 1;
  let hasNextPage = true;
  while (hasNextPage) {
    const response = await fetch(`${serverApiUrl}/api/v1/recipes?page=${page}&pageSize=50`, {
      cache: "no-store",
    });
    if (!response.ok) {
      throw new Error(`Recipe API returned ${response.status}`);
    }
    const body = (await response.json()) as {
      items: { slug: string; createdAt: string }[];
      hasNextPage: boolean;
    };
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
