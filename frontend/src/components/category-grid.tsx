import Image from "next/image";
import Link from "next/link";
import { useTranslations } from "next-intl";

export type Category = {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  image_url: string | null;
  recipe_count: number;
};

const previewDishes = ["/images/vietnamese-table.png", "/images/breakfast.png", "/images/plant-based.png", "/images/dessert.png"];

function previewForCategory(name: string, index: number): string {
  const normalized = name.toLowerCase();
  if (normalized.includes("viet") || normalized.includes("pho") || normalized.includes("phở")) return "/images/vietnamese-table.png";
  if (normalized.includes("breakfast")) return "/images/breakfast.png";
  if (normalized.includes("plant") || normalized.includes("vegetable")) return "/images/plant-based.png";
  if (normalized.includes("baking") || normalized.includes("dessert")) return "/images/dessert.png";
  return previewDishes[index % previewDishes.length];
}

export function CategoryGrid({ categories }: { categories: Category[] }) {
  const t = useTranslations("category");
  if (categories.length === 0) {
    return <div className="empty-state"><span aria-hidden="true">✳</span><h3>{t("emptyTitle")}</h3><p>{t("emptyDescription")}</p></div>;
  }

  return <div className="category-grid">{categories.map((category, index) => (
    <article className="category-card" key={category.id}>
      <div className="category-card-art"><span className="category-number">{String(index + 1).padStart(2, "0")}</span><div className={`category-dish${category.image_url ? " custom-image" : ""}`}><Image src={category.image_url || previewForCategory(category.name, index)} alt="" fill unoptimized={Boolean(category.image_url)} sizes="(max-width: 560px) 85vw, (max-width: 1100px) 42vw, 22vw" /></div></div>
      <div className="category-card-body"><p className="category-card-meta">{t("label")}</p><h3><Link href={`/categories/${category.slug}`}>{category.name}</Link></h3><p>{category.description ?? t("fallback")}</p><span className="recipe-count">{t("recipeCount", { count: category.recipe_count })}<span aria-hidden="true">↗</span></span></div>
    </article>
  ))}</div>;
}
