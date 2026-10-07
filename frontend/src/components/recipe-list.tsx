"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import type { Category } from "@/components/category-grid";
import {
  getRecipeList,
  type PagedRecipeList,
  type RecipeListDifficulty,
  type RecipeListParams,
  type RecipeListSort,
} from "@/lib/api/recipe-list";
import {
  AUTH_SESSION_CHANGED,
  clearAuthSession,
  loadActiveAuthSession,
  type AuthSession,
} from "@/lib/auth-session";
import styles from "./recipe-list.module.css";

type Filters = {
  search: string;
  categoryId: string;
  difficulty: "" | RecipeListDifficulty;
  maxCookTime: string;
  minServings: string;
  sort: RecipeListSort;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const defaultFilters: Filters = {
  search: "",
  categoryId: "",
  difficulty: "",
  maxCookTime: "",
  minServings: "",
  sort: "-createdAt",
};

function toOptionalPositiveInteger(value: string): number | undefined {
  const parsed = Number(value);
  return Number.isInteger(parsed) && parsed >= 0 ? parsed : undefined;
}

export function RecipeList() {
  const t = useTranslations("recipeList");
  const [session, setSession] = useState<AuthSession | null | undefined>(undefined);
  const [categories, setCategories] = useState<Category[]>([]);
  const [filters, setFilters] = useState<Filters>(defaultFilters);
  const [appliedFilters, setAppliedFilters] = useState<Filters>(defaultFilters);
  const [page, setPage] = useState(1);
  const [result, setResult] = useState<PagedRecipeList | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [reload, setReload] = useState(0);

  useEffect(() => {
    const updateSession = () => void loadActiveAuthSession().then(setSession);
    updateSession();
    window.addEventListener(AUTH_SESSION_CHANGED, updateSession);
    return () => window.removeEventListener(AUTH_SESSION_CHANGED, updateSession);
  }, []);

  useEffect(() => {
    let active = true;
    async function loadCategories() {
      try {
        const response = await fetch(`${apiUrl}/api/v1/categories`, { cache: "no-store" });
        if (!response.ok) throw new Error("categories");
        if (active) setCategories((await response.json()) as Category[]);
      } catch {
        if (active) setCategories([]);
      }
    }
    void loadCategories();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    async function loadRecipes() {
      await Promise.resolve();
      if (session === undefined) return;
      const request: RecipeListParams = {
        page,
        pageSize: 12,
        sort: appliedFilters.sort,
        ...(appliedFilters.search ? { q: appliedFilters.search } : {}),
        ...(appliedFilters.categoryId ? { categoryId: appliedFilters.categoryId } : {}),
        ...(appliedFilters.difficulty ? { difficulty: appliedFilters.difficulty } : {}),
        ...(toOptionalPositiveInteger(appliedFilters.maxCookTime) !== undefined
          ? { maxCookTime: toOptionalPositiveInteger(appliedFilters.maxCookTime) }
          : {}),
        ...(toOptionalPositiveInteger(appliedFilters.minServings) !== undefined
          ? { minServings: toOptionalPositiveInteger(appliedFilters.minServings) }
          : {}),
      };
      if (!active) return;
      setLoading(true);
      setError(false);
      try {
        const nextResult = await getRecipeList(request, session?.accessToken);
        if (active) setResult(nextResult);
      } catch (requestError) {
        if (requestError instanceof Error && "status" in requestError && requestError.status === 401) {
          clearAuthSession();
        }
        if (active) setError(true);
      } finally {
        if (active) setLoading(false);
      }
    }
    void loadRecipes();
    return () => { active = false; };
  }, [appliedFilters, page, reload, session]);

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    setAppliedFilters({ ...filters, search: filters.search.trim() });
  }

  function resetFilters() {
    setFilters(defaultFilters);
    setAppliedFilters(defaultFilters);
    setPage(1);
  }

  const totalTime = (prepTime: number, cookTime: number) => prepTime + cookTime;

  return (
    <main id="main-content" className={styles.page}>
      <section className={styles.intro}>
        <div>
          <Link className={styles.back} href="/">← {t("back")}</Link>
          <h1>{t("title")}</h1>
          <p>{t("description")}</p>
        </div>
        <Link className={styles.create} href="/recipes/new">{t("create")} <span aria-hidden="true">↗</span></Link>
      </section>

      <section className={styles.content} aria-label={t("title")}>
        <form className={styles.filters} onSubmit={applyFilters}>
          <label className={styles.searchField}>
            <span>{t("search")}</span>
            <input type="search" minLength={2} maxLength={100} placeholder={t("searchPlaceholder")} value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} />
          </label>
          <label>
            <span>{t("category")}</span>
            <select value={filters.categoryId} onChange={(event) => setFilters({ ...filters, categoryId: event.target.value })}>
              <option value="">{t("allCategories")}</option>
              {categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}
            </select>
          </label>
          <label>
            <span>{t("difficulty")}</span>
            <select value={filters.difficulty} onChange={(event) => setFilters({ ...filters, difficulty: event.target.value as Filters["difficulty"] })}>
              <option value="">{t("allDifficulties")}</option>
              {(["Easy", "Medium", "Hard", "Expert"] as const).map((difficulty, index) => <option key={difficulty} value={difficulty}>{t(`difficulty${index + 1}`)}</option>)}
            </select>
          </label>
          <label>
            <span>{t("maxCookTime")}</span>
            <input type="number" min="0" inputMode="numeric" placeholder={t("minutes")} value={filters.maxCookTime} onChange={(event) => setFilters({ ...filters, maxCookTime: event.target.value })} />
          </label>
          <label>
            <span>{t("minServings")}</span>
            <input type="number" min="1" inputMode="numeric" placeholder={t("people")} value={filters.minServings} onChange={(event) => setFilters({ ...filters, minServings: event.target.value })} />
          </label>
          <label>
            <span>{t("sort")}</span>
            <select value={filters.sort} onChange={(event) => setFilters({ ...filters, sort: event.target.value as RecipeListSort })}>
              <option value="-createdAt">{t("sortNewest")}</option>
              <option value="createdAt">{t("sortOldest")}</option>
              <option value="title">{t("sortTitleAsc")}</option>
              <option value="-title">{t("sortTitleDesc")}</option>
              <option value="cookTime">{t("sortCookAsc")}</option>
              <option value="-cookTime">{t("sortCookDesc")}</option>
            </select>
          </label>
          <div className={styles.actions}>
            <button className={styles.apply} type="submit" disabled={loading}>{loading ? t("loading") : t("apply")}</button>
            <button className={styles.reset} type="button" onClick={resetFilters} disabled={loading}>{t("reset")}</button>
          </div>
        </form>

        {error ? (
          <section className={`${styles.state} ${styles.error}`} role="alert">
            <h2>{t("errorTitle")}</h2><p>{t("errorDescription")}</p>
            <button type="button" onClick={() => setReload((value) => value + 1)}>{t("retry")}</button>
          </section>
        ) : loading ? (
          <section className={styles.skeletonSection} aria-label={t("loading")} aria-busy="true" aria-live="polite">
            <p className={styles.visuallyHidden}>{t("loading")}</p>
            <div className={styles.grid} aria-hidden="true">
              {Array.from({ length: 6 }, (_, index) => (
                <div className={styles.skeletonCard} key={index}>
                  <div className={styles.skeletonTag} />
                  <div className={styles.skeletonTitle} />
                  <div className={styles.skeletonLine} />
                  <div className={styles.skeletonLineShort} />
                </div>
              ))}
            </div>
          </section>
        ) : result && result.items.length === 0 ? (
          <section className={styles.state}><h2>{t("emptyTitle")}</h2><p>{t("emptyDescription")}</p></section>
        ) : result ? (
          <>
            <p className={styles.count}>{t("resultCount", { count: result.totalCount })}</p>
            <div className={styles.grid} aria-busy={loading}>
              {result.items.map((recipe) => (
                <article className={styles.card} key={recipe.id}>
                  <Link className={styles.cardOverlay} href={`/recipes/${recipe.slug}`} aria-label={t("viewRecipe", { title: recipe.title })} />
                  <div className={styles.cardTop}><Link href={`/categories/${recipe.category.slug}`}>{recipe.category.name}</Link><span className={styles.status}>{t(`status${recipe.status}`)}</span></div>
                  <h2>{recipe.title}</h2>
                  <p>{recipe.description}</p>
                  <dl>
                    <div><dt>{t("totalTime")}</dt><dd>{t("minuteCount", { count: totalTime(recipe.prepTimeMinutes, recipe.cookTimeMinutes) })}</dd></div>
                    <div><dt>{t("servings")}</dt><dd>{t("servingCount", { count: recipe.servings })}</dd></div>
                    <div><dt>{t("difficulty")}</dt><dd>{t(`difficulty${recipe.difficulty}`)}</dd></div>
                  </dl>
                  <span className={styles.viewDetail}>{t("viewDetail")} <span aria-hidden="true">→</span></span>
                </article>
              ))}
            </div>
            <nav className={styles.pagination} aria-label={t("pagination")}>
              <button type="button" onClick={() => setPage((current) => current - 1)} disabled={!result.hasPreviousPage || loading}>{t("previous")}</button>
              <span>{t("pageOf", { page: result.page, total: result.totalPages || 1 })}</span>
              <button type="button" onClick={() => setPage((current) => current + 1)} disabled={!result.hasNextPage || loading}>{t("next")}</button>
            </nav>
          </>
        ) : null}
      </section>
    </main>
  );
}
