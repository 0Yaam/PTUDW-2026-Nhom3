"use client";

import { useEffect, useState } from "react";
import Image from "next/image";
import Link from "next/link";
import { useTranslations } from "next-intl";
import type { Category } from "@/components/category-grid";
import { previewForCategory } from "@/components/category-grid";
import { getCategories } from "@/lib/api/categories";
import { getRecipeList, type RecipeListItem } from "@/lib/api/recipe-list";
import { EmptyState, ErrorState } from "@/components/ui/feedback";
import styles from "./home-feed.module.css";

export type HomeFeedProps = {
  initialCategories?: Category[];
  initialRecipes?: RecipeListItem[];
  initialCategoriesError?: boolean;
  initialRecipesError?: boolean;
};

export function HomeFeed({
  initialCategories,
  initialRecipes,
  initialCategoriesError = false,
  initialRecipesError = false,
}: HomeFeedProps) {
  const t = useTranslations("home");
  const tRecipeList = useTranslations("recipeList");
  const tCategory = useTranslations("category");

  const [categories, setCategories] = useState<Category[]>(initialCategories ?? []);
  const [categoriesLoading, setCategoriesLoading] = useState(
    initialCategories === undefined && !initialCategoriesError,
  );
  const [categoriesError, setCategoriesError] = useState(initialCategoriesError);

  const [recipes, setRecipes] = useState<RecipeListItem[]>(initialRecipes ?? []);
  const [recipesLoading, setRecipesLoading] = useState(
    initialRecipes === undefined && !initialRecipesError,
  );
  const [recipesError, setRecipesError] = useState(initialRecipesError);

  async function reloadCategories() {
    setCategoriesLoading(true);
    setCategoriesError(false);
    try {
      const data = await getCategories();
      setCategories(data);
    } catch {
      setCategoriesError(true);
    } finally {
      setCategoriesLoading(false);
    }
  }

  async function reloadRecipes() {
    setRecipesLoading(true);
    setRecipesError(false);
    try {
      const data = await getRecipeList({ page: 1, pageSize: 6, sort: "-createdAt" });
      setRecipes(data.items);
    } catch {
      setRecipesError(true);
    } finally {
      setRecipesLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    if (initialCategories === undefined && !initialCategoriesError) {
      void getCategories()
        .then((data) => {
          if (active) {
            setCategories(data);
            setCategoriesLoading(false);
          }
        })
        .catch(() => {
          if (active) {
            setCategoriesError(true);
            setCategoriesLoading(false);
          }
        });
    }
    if (initialRecipes === undefined && !initialRecipesError) {
      void getRecipeList({ page: 1, pageSize: 6, sort: "-createdAt" })
        .then((data) => {
          if (active) {
            setRecipes(data.items);
            setRecipesLoading(false);
          }
        })
        .catch(() => {
          if (active) {
            setRecipesError(true);
            setRecipesLoading(false);
          }
        });
    }
    return () => {
      active = false;
    };
  }, [initialCategories, initialCategoriesError, initialRecipes, initialRecipesError]);


  return (
    <section className={styles.section} aria-labelledby="home-feed-title">
      <div className={styles.layout}>
        <div className={styles.mainColumn}>
          <div className={styles.header}>
            <div>
              <p className={styles.eyebrow}>{t("latestRecipesEyebrow")}</p>
              <h2 id="home-feed-title" className={styles.heading}>
                {t("latestRecipesTitle")}
              </h2>
              <p className={styles.description}>{t("latestRecipesDescription")}</p>
            </div>
            <Link className={styles.allLink} href="/recipes">
              {t("viewAllRecipes")} <span aria-hidden="true">→</span>
            </Link>
          </div>

          {recipesError ? (
            <ErrorState
              title={t("recipesErrorTitle")}
              description={t("recipesErrorDescription")}
              action={{
                label: t("retry"),
                onClick: reloadRecipes,
                disabled: recipesLoading,
              }}
            />
          ) : recipesLoading ? (
            <div
              className={styles.recipeGrid}
              aria-label={t("recipesLoading")}
              aria-busy="true"
            >
              {Array.from({ length: 6 }).map((_, index) => (
                <div className={styles.skeletonCard} key={index}>
                  <div className={`${styles.skeletonLine} ${styles.skeletonLineShort}`} />
                  <div className={`${styles.skeletonLine} ${styles.skeletonTitle}`} />
                  <div className={styles.skeletonLine} />
                  <div className={`${styles.skeletonLine} ${styles.skeletonLineShort}`} />
                </div>
              ))}
            </div>
          ) : recipes.length === 0 ? (
            <EmptyState
              title={t("recipesEmptyTitle")}
              description={t("recipesEmptyDescription")}
            />
          ) : (
            <div className={styles.recipeGrid}>
              {recipes.map((recipe) => (
                <article className={styles.recipeCard} key={recipe.id}>
                  <Link
                    className={styles.cardOverlay}
                    href={`/recipes/${recipe.slug}`}
                    aria-label={tRecipeList("viewRecipe", { title: recipe.title })}
                  />
                  <div className={styles.cardTop}>
                    <Link href={`/categories/${recipe.category.slug}`}>
                      {recipe.category.name}
                    </Link>
                    <span className={styles.status}>
                      {tRecipeList(`status${recipe.status}`)}
                    </span>
                  </div>
                  <h3>{recipe.title}</h3>
                  <p>{recipe.description}</p>
                  <dl className={styles.facts}>
                    <div>
                      <dt>{tRecipeList("totalTime")}</dt>
                      <dd>
                      {tRecipeList("minuteCount", {
                        count: recipe.prepTimeMinutes + recipe.cookTimeMinutes,
                      })}
                      </dd>
                    </div>
                    <div>
                      <dt>{tRecipeList("servings")}</dt>
                      <dd>
                        {tRecipeList("servingCount", { count: recipe.servings })}
                      </dd>
                    </div>
                    <div>
                      <dt>{tRecipeList("difficulty")}</dt>
                      <dd>{tRecipeList(`difficulty${recipe.difficulty}`)}</dd>
                    </div>
                  </dl>
                  <span className={styles.viewDetail}>
                    {tRecipeList("viewDetail")} <span aria-hidden="true">→</span>
                  </span>
                </article>
              ))}
            </div>
          )}
        </div>

        <aside
          className={styles.sidebar}
          id="categories"
          aria-labelledby="categories-sidebar-title"
        >
          <div className={styles.sidebarHeader}>
            <div>
              <p className={styles.eyebrow}>{t("categoriesSidebarDescription")}</p>
              <h2 id="categories-sidebar-title" className={styles.sidebarTitle}>
                {t("categoriesSidebarTitle")}
              </h2>
            </div>
            <Link className={styles.allLink} href="/categories">
              {t("viewAllCategories")} <span aria-hidden="true">→</span>
            </Link>
          </div>

          {categoriesError ? (
            <ErrorState
              title={t("categoriesErrorTitle")}
              description={t("categoriesErrorDescription")}
              action={{
                label: t("retry"),
                onClick: reloadCategories,
                disabled: categoriesLoading,
              }}
            />
          ) : categoriesLoading ? (
            <div
              className={styles.categoryList}
              aria-label={t("categoriesLoading")}
              aria-busy="true"
            >
              {Array.from({ length: 4 }).map((_, index) => (
                <div className={styles.skeletonCategoryItem} key={index}>
                  <div className={styles.skeletonThumb} />
                  <div className={styles.skeletonInfo}>
                    <div
                      className={`${styles.skeletonLine} ${styles.skeletonLineShort}`}
                    />
                    <div className={styles.skeletonLine} style={{ width: "35%" }} />
                  </div>
                </div>
              ))}
            </div>
          ) : categories.length === 0 ? (
            <EmptyState
              title={t("categoriesEmptyTitle")}
              description={t("categoriesEmptyDescription")}
            />
          ) : (
            <nav
              className={styles.categoryList}
              aria-label={t("categoriesSidebarTitle")}
            >
              {categories.map((category, index) => (
                <Link
                  className={styles.categoryItem}
                  key={category.id}
                  href={`/categories/${category.slug}`}
                >
                  <div className={styles.categoryThumb}>
                    <Image
                      src={
                        category.image_url ||
                        previewForCategory(category.name, index)
                      }
                      alt=""
                      fill
                      sizes="52px"
                    />
                  </div>
                  <div className={styles.categoryInfo}>
                    <span className={styles.categoryName}>{category.name}</span>
                    <span className={styles.categoryCount}>
                      {tCategory("recipeCount", { count: category.recipe_count })}
                    </span>
                  </div>
                  <span className={styles.categoryArrow} aria-hidden="true">
                    →
                  </span>
                </Link>
              ))}
            </nav>
          )}
        </aside>
      </div>
    </section>
  );
}
