import Link from "next/link";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { getRecipe, type RecipeDetail } from "@/lib/api/recipes";
import { siteUrl } from "@/lib/site-url";

const difficultyKeys = ["difficulty1", "difficulty2", "difficulty3", "difficulty4"] as const;

function difficultyKey(value: number) {
  return difficultyKeys[value - 1] ?? difficultyKeys[0];
}

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
    ...(nutrition && Object.values(nutrition).some((value) => value !== undefined)
      ? {
          nutrition: {
            "@type": "NutritionInformation",
            ...(nutrition.calories !== undefined && { calories: `${nutrition.calories} kcal` }),
            ...(nutrition.protein !== undefined && { proteinContent: `${nutrition.protein} g` }),
            ...(nutrition.carbohydrates !== undefined && {
              carbohydrateContent: `${nutrition.carbohydrates} g`,
            }),
            ...(nutrition.fat !== undefined && { fatContent: `${nutrition.fat} g` }),
            ...(nutrition.fiber !== undefined && { fiberContent: `${nutrition.fiber} g` }),
            ...(nutrition.sodium !== undefined && { sodiumContent: `${nutrition.sodium} mg` }),
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
  const [recipe, t, tc] = await Promise.all([
    getRecipe(slug),
    getTranslations("recipeDetail"),
    getTranslations("category"),
  ]);

  if (!recipe) {
    return (
      <main id="main-content" className="error-shell">
        <p className="eyebrow">{t("notFoundEyebrow")}</p>
        <h1>{t("notFoundTitle")}</h1>
        <p>{t("notFoundDescription")}</p>
        <Link className="primary-action" href="/#categories">
          {t("notFoundAction")} <span aria-hidden="true">↗</span>
        </Link>
      </main>
    );
  }

  return (
    <main id="main-content" className="detail-shell">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(recipeStructuredData(recipe)) }}
      />
      <Link className="back-link" href={`/categories/${recipe.category.slug}`}>
        <span aria-hidden="true">←</span> {t("back")}
      </Link>

      <header className="detail-header">
        <p className="eyebrow">{t("eyebrow")}</p>
        <h1>{recipe.title}</h1>
        <p className="lead">{recipe.description}</p>
        <p className="detail-count">{t("byAuthor", { name: recipe.author.fullName })}</p>
      </header>

      <section className="recipe-detail-facts" aria-label={tc("totalTimeLabel")}>
        <dl className="recipe-card-facts">
          <div>
            <dt>{tc("totalTimeLabel")}</dt>
            <dd>
              {tc("totalTime", { minutes: recipe.prepTimeMinutes + recipe.cookTimeMinutes })}
            </dd>
          </div>
          <div>
            <dt>{tc("servingsLabel")}</dt>
            <dd>{tc("servings", { count: recipe.servings })}</dd>
          </div>
          <div>
            <dt>{tc("label")}</dt>
            <dd>{tc(difficultyKey(recipe.difficulty))}</dd>
          </div>
        </dl>
      </section>

      <section className="detail-recipes" aria-labelledby="ingredients-title">
        <h2 id="ingredients-title">{t("ingredientsTitle")}</h2>
        <ul className="ingredient-list">
          {recipe.ingredients.map((ingredient) => (
            <li key={ingredient.id}>
              <span className="ingredient-amount">
                {ingredient.quantity} {ingredient.unit}
              </span>
              <span>{ingredient.name}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="detail-recipes" aria-labelledby="steps-title">
        <h2 id="steps-title">{t("stepsTitle")}</h2>
        <ol className="step-list">
          {recipe.steps.map((step) => (
            <li key={step.id}>
              <p>{step.instruction}</p>
              {step.durationMinutes !== null && (
                <span className="step-duration">
                  {t("stepDuration", { minutes: step.durationMinutes })}
                </span>
              )}
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
