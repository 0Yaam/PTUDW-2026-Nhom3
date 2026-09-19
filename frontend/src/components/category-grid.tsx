import Link from "next/link";

export type Category = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  image_url: string | null;
  recipe_count: number;
};

const accents = ["accent-clay", "accent-leaf", "accent-saffron", "accent-ink"];

export function CategoryGrid({ categories }: { categories: Category[] }) {
  if (categories.length === 0) {
    return (
      <div className="empty-state">
        <span>No categories yet</span>
        <p>Run the seed command from the README to add the starter data.</p>
      </div>
    );
  }

  return (
    <div className="category-grid">
      {categories.map((category, index) => (
        <Link
          className={`category-card ${accents[index % accents.length]}`}
          href={`/categories/${category.slug}`}
          key={category.id}
        >
          <span className="card-index">{String(index + 1).padStart(2, "0")}</span>
          <div className="card-symbol" aria-hidden="true">
            {category.name.slice(0, 1)}
          </div>
          <h3>{category.name}</h3>
          <p>{category.description ?? "This category is ready for its first recipe."}</p>
          <span className="recipe-count">
            {category.recipe_count} {category.recipe_count === 1 ? "recipe" : "recipes"}
          </span>
        </Link>
      ))}
    </div>
  );
}
