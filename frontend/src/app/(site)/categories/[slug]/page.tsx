import Link from "next/link";
import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { getCategory, type RecipeCard } from "@/lib/api/categories";
import { siteUrl } from "@/lib/site-url";

const difficultyKeys = ["difficulty1", "difficulty2", "difficulty3", "difficulty4"] as const;

function difficultyKey(value: number) {
  return difficultyKeys[value - 1] ?? difficultyKeys[0];
}

export async function generateMetadata({
  params,
}: {
  params: Promise<{ slug: string }>;
}): Promise<Metadata> {
  const { slug } = await params;
  const category = await getCategory(slug);

  if (!category) {
    return { title: "Category not found", robots: { index: false, follow: false } };
  }

  return {
    title: category.name,
    description: category.description ?? undefined,
    alternates: { canonical: siteUrl(`/categories/${category.slug}`) },
  };
}

export default async function CategoryDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const [category, t] = await Promise.all([getCategory(slug), getTranslations("category")]);

  // Rendered here rather than through notFound(): a not-found.tsx boundary is
  // rendered outside the next-intl request scope, so its translated copy never
  // reaches the server-rendered HTML.
  if (!category) {
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

  const structuredData = {
    "@context": "https://schema.org",
    "@type": "CollectionPage",
    name: category.name,
    description: category.description ?? undefined,
    mainEntity: {
      "@type": "ItemList",
      itemListElement: category.recipes.map((recipe, index) => ({
        "@type": "ListItem",
        position: index + 1,
        url: siteUrl(`/recipes/${recipe.slug}`),
        name: recipe.title,
      })),
    },
  };

  return (
    <main id="main-content" className="detail-shell">
      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{ __html: JSON.stringify(structuredData) }}
      />
      <Link className="back-link" href="/#categories">
        <span aria-hidden="true">←</span> {t("back")}
      </Link>

      <header className="detail-header">
        <p className="eyebrow">{t("detailLabel")}</p>
        <h1>{category.name}</h1>
        <p className="lead">{category.description ?? t("fallback")}</p>
        <p className="detail-count">{t("recipeCount", { count: category.recipe_count })}</p>
      </header>

      <section className="detail-recipes" aria-labelledby="recipes-title">
        <h2 id="recipes-title">{t("recipesTitle")}</h2>

        {category.recipes.length === 0 ? (
          <div className="empty-state">
            <span aria-hidden="true">✳</span>
            <h3>{t("noRecipesTitle")}</h3>
            <p>{t("noRecipesDescription")}</p>
          </div>
        ) : (
          <ul className="recipe-cards">
            {category.recipes.map((recipe: RecipeCard) => (
              <li className="recipe-card" key={recipe.id}>
                <p className="recipe-card-meta">{t(difficultyKey(recipe.difficulty))}</p>
                <h3><Link href={`/recipes/${recipe.slug}`}>{recipe.title}</Link></h3>
                <p className="recipe-card-description">{recipe.description}</p>
                <dl className="recipe-card-facts">
                  <div>
                    <dt>{t("totalTimeLabel")}</dt>
                    <dd>
                      {t("totalTime", {
                        minutes: recipe.prep_time_minutes + recipe.cook_time_minutes,
                      })}
                    </dd>
                  </div>
                  <div>
                    <dt>{t("servingsLabel")}</dt>
                    <dd>{t("servings", { count: recipe.servings })}</dd>
                  </div>
                </dl>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
