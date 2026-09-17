import Link from "next/link";
import { notFound } from "next/navigation";

import { getCategory } from "@/lib/api/categories";

export default async function CategoryDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  const category = await getCategory(slug);

  if (!category) {
    notFound();
  }

  return (
    <main className="detail-shell">
      <Link className="back-link" href="/#categories">
        <span aria-hidden="true">&lt;-</span> All categories
      </Link>

      <header className="detail-header">
        <p className="eyebrow">Category</p>
        <h1>{category.name}</h1>
        <p className="lead">
          {category.description ?? "This category is ready for its first recipe."}
        </p>
        <p className="recipe-count">
          {category.recipes.length} {category.recipes.length === 1 ? "recipe" : "recipes"}
        </p>
      </header>

      <section aria-labelledby="recipes-title">
        <h2 id="recipes-title" className="detail-subtitle">
          Recipes
        </h2>
        {category.recipes.length === 0 ? (
          <div className="empty-state">
            <span>No recipes yet</span>
            <p>This category is waiting for its first recipe. Come back soon.</p>
          </div>
        ) : (
          <ul className="recipe-cards">
            {category.recipes.map((recipe) => (
              <li className="recipe-card" key={recipe.id}>
                <h3>{recipe.title}</h3>
                <p className="recipe-meta">
                  {[
                    recipe.cook_time_minutes ? `${recipe.cook_time_minutes} min` : null,
                    recipe.difficulty,
                  ]
                    .filter(Boolean)
                    .join(" - ") || "Details coming soon"}
                </p>
              </li>
            ))}
          </ul>
        )}
      </section>
    </main>
  );
}
