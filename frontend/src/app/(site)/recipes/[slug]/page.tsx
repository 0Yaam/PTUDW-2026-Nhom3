import type { Metadata } from "next";

import { RecipeDetailView } from "@/components/recipe-detail-view";
import { getRecipe, type RecipeDetail } from "@/lib/api/recipes";
import { siteUrl } from "@/lib/site-url";

function isoDuration(minutes: number): string {
  return `PT${minutes}M`;
}

function recipeStructuredData(recipe: RecipeDetail) {
  const nutrition = recipe.nutrition;
  return {
    "@context": "https://schema.org",
    "@type": "Recipe",
    name: recipe.title,
    description: recipe.description,
    author: { "@type": "Person", name: recipe.author.fullName },
    recipeCategory: recipe.category.name,
    recipeYield: String(recipe.servings),
    prepTime: isoDuration(recipe.prepTimeMinutes),
    cookTime: isoDuration(recipe.cookTimeMinutes),
    totalTime: isoDuration(recipe.prepTimeMinutes + recipe.cookTimeMinutes),
    recipeIngredient: recipe.ingredients.map(
      (ingredient) => `${ingredient.quantity} ${ingredient.unit} ${ingredient.name}`,
    ),
    recipeInstructions: recipe.steps.map((step) => ({
      "@type": "HowToStep",
      position: step.stepNumber,
      text: step.instruction,
    })),
    ...(nutrition && Object.values(nutrition).some((value) => value != null)
      ? {
          nutrition: {
            "@type": "NutritionInformation",
            ...(nutrition.calories != null && { calories: `${nutrition.calories} kcal` }),
            ...(nutrition.protein != null && { proteinContent: `${nutrition.protein} g` }),
            ...(nutrition.carbohydrates != null && {
              carbohydrateContent: `${nutrition.carbohydrates} g`,
            }),
            ...(nutrition.fat != null && { fatContent: `${nutrition.fat} g` }),
            ...(nutrition.fiber != null && { fiberContent: `${nutrition.fiber} g` }),
            ...(nutrition.sodium != null && { sodiumContent: `${nutrition.sodium} mg` }),
          },
        }
      : {}),
  };
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const recipe = await getRecipe(slug);

  if (!recipe) {
    return { title: "Recipe not found", robots: { index: false, follow: false } };
  }

  return {
    title: recipe.title,
    description: recipe.description,
    alternates: { canonical: siteUrl(`/recipes/${recipe.slug}`) },
    openGraph: {
      title: recipe.title,
      description: recipe.description,
      type: "article",
      url: siteUrl(`/recipes/${recipe.slug}`),
    },
  };
}

export default async function RecipeDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const recipe = await getRecipe(slug);

  return (
    <>
      {recipe && (
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(recipeStructuredData(recipe)) }}
        />
      )}
      <RecipeDetailView slug={slug} />
    </>
  );
}
