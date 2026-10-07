"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { getRecipeDetail, RecipeApiError, type RecipeDetail } from "@/lib/api/recipes";
import {
  AUTH_SESSION_CHANGED,
  clearAuthSession,
  loadActiveAuthSession,
  type AuthSession,
} from "@/lib/auth-session";
import styles from "./recipe-detail-view.module.css";

type NutritionKey = "calories" | "protein" | "carbohydrates" | "fat" | "fiber" | "sodium";
const nutritionKeys: NutritionKey[] = [
  "calories", "protein", "carbohydrates", "fat", "fiber", "sodium",
];

export function RecipeDetailView({ slug }: { slug: string }) {
  const t = useTranslations("recipeDetail");
  const locale = useLocale();
  const [session, setSession] = useState<AuthSession | null | undefined>(undefined);
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [reload, setReload] = useState(0);
  const [activeImageId, setActiveImageId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const updateSession = () => void loadActiveAuthSession().then((value) => {
      if (active) setSession(value);
    });
    updateSession();
    window.addEventListener(AUTH_SESSION_CHANGED, updateSession);
    return () => {
      active = false;
      window.removeEventListener(AUTH_SESSION_CHANGED, updateSession);
    };
  }, []);

  useEffect(() => {
    if (session === undefined) return;
    let active = true;
    async function load() {
      setLoading(true);
      setErrorStatus(null);
      setRecipe(null);
      try {
        const detail = await getRecipeDetail(slug, session?.accessToken);
        if (!active) return;
        setRecipe(detail);
        setActiveImageId(detail.images.find((image) => image.isPrimary)?.id ?? detail.images[0]?.id ?? null);
      } catch (error) {
        if (!active) return;
        if (error instanceof RecipeApiError && error.status === 401) clearAuthSession();
        setErrorStatus(error instanceof RecipeApiError ? error.status : 0);
      } finally {
        if (active) setLoading(false);
      }
    }
    void load();
    return () => { active = false; };
  }, [slug, session, reload]);

  const formatNumber = (value: number) => new Intl.NumberFormat(locale).format(value);
  const activeImage = recipe?.images.find((image) => image.id === activeImageId) ?? recipe?.images[0];
  const nutrients = recipe?.nutrition
    ? nutritionKeys.filter((key) => recipe.nutrition?.[key] !== null)
    : [];

  return (
    <main id="main-content" className={styles.page}>
      <div className={styles.shell}>
        <Link className={styles.back} href="/recipes">← {t("back")}</Link>

        {loading ? (
          <div className={styles.skeleton} aria-busy="true" aria-label={t("loading")}>
            <span className={styles.visuallyHidden}>{t("loading")}</span>
            <div className={styles.skeletonHero}><div className={styles.skeletonCopy}><i /><i /><i /></div><div className={styles.skeletonImage} /></div>
            <div className={styles.skeletonFacts}><i /><i /><i /><i /></div>
            <div className={styles.skeletonBody}><i /><i /></div>
          </div>
        ) : errorStatus !== null ? (
          <section className={styles.state} role={errorStatus === 404 ? undefined : "alert"}>
            <span className={styles.stateIcon} aria-hidden="true">✳</span>
            <h1>{errorStatus === 404 ? t("notFoundTitle") : errorStatus === 403 || errorStatus === 401 ? t("privateTitle") : t("errorTitle")}</h1>
            <p>{errorStatus === 404 ? t("notFoundDescription") : errorStatus === 403 || errorStatus === 401 ? t("privateDescription") : t("errorDescription")}</p>
            {errorStatus !== 404 && <button type="button" onClick={() => setReload((value) => value + 1)}>{t("retry")}</button>}
          </section>
        ) : recipe ? (
          <>
            <header className={`${styles.hero} ${activeImage ? "" : styles.heroNoImage}`}>
              <div className={styles.heroCopy}>
                <div className={styles.kicker}>
                  <Link href={`/categories/${recipe.category.slug}`}>{recipe.category.name}</Link>
                  {recipe.status !== "Published" && <span>{t(`status${recipe.status}`)}</span>}
                </div>
                <h1>{recipe.title}</h1>
                <p className={styles.description}>{recipe.description}</p>
                <p className={styles.byline}>{t("byAuthor")}</p>
              </div>
              <div className={styles.heroMedia}>
                {activeImage ? (
                  <Image
                    src={activeImage.mediumUrl ?? activeImage.originalUrl}
                    alt={activeImage.altText ?? recipe.title}
                    fill
                    unoptimized
                    sizes="(max-width: 760px) 100vw, 50vw"
                    className={styles.heroImage}
                  />
                ) : (
                  <div className={styles.imagePlaceholder}>
                    <span aria-hidden="true">✳</span>
                    <p>{t("noImage")}</p>
                  </div>
                )}
              </div>
            </header>

            {recipe.images.length > 1 && (
              <div className={styles.gallery} aria-label={t("gallery")}>
                {recipe.images.map((image, index) => (
                  <button
                    type="button"
                    key={image.id}
                    className={image.id === activeImage?.id ? styles.selectedImage : ""}
                    aria-label={t("imageNumber", { number: index + 1 })}
                    aria-pressed={image.id === activeImage?.id}
                    onClick={() => setActiveImageId(image.id)}
                  >
                    <Image src={image.thumbnailUrl ?? image.originalUrl} alt="" fill unoptimized sizes="80px" />
                  </button>
                ))}
              </div>
            )}

            <section className={styles.overview} aria-labelledby="recipe-overview-title">
              <h2 id="recipe-overview-title">{t("overview")}</h2>
              <dl className={styles.facts}>
                <div><dt>{t("prepTime")}</dt><dd>{t("minutes", { count: recipe.prepTimeMinutes })}</dd></div>
                <div><dt>{t("cookTime")}</dt><dd>{t("minutes", { count: recipe.cookTimeMinutes })}</dd></div>
                <div><dt>{t("servings")}</dt><dd>{t("servingCount", { count: recipe.servings })}</dd></div>
                <div><dt>{t("difficulty")}</dt><dd>{t(`difficulty${recipe.difficulty}`)}</dd></div>
              </dl>
            </section>

            <nav className={styles.sectionNav} aria-label={t("jumpTo")}>
              <span>{t("jumpTo")}</span>
              <a href="#recipe-ingredients-title">{t("ingredients")}</a>
              <a href="#recipe-steps-title">{t("steps")}</a>
              {nutrients.length > 0 && <a href="#recipe-nutrition-title">{t("nutrition")}</a>}
            </nav>

            <div className={styles.bodyGrid}>
              <section className={styles.ingredients} aria-labelledby="recipe-ingredients-title">
                <p className={styles.sectionKicker}>{t("ingredientsKicker")}</p>
                <h2 id="recipe-ingredients-title">{t("ingredients")}</h2>
                {recipe.ingredients.length ? (
                  <ul>
                    {recipe.ingredients.map((item) => (
                      <li key={item.id}>
                        <span>{item.name}</span>
                        <strong>{formatNumber(item.quantity)} {item.unit}</strong>
                      </li>
                    ))}
                  </ul>
                ) : <p className={styles.emptySection}>{t("noIngredients")}</p>}
              </section>

              <section className={styles.method} aria-labelledby="recipe-steps-title">
                <p className={styles.sectionKicker}>{t("stepsKicker")}</p>
                <h2 id="recipe-steps-title">{t("steps")}</h2>
                {recipe.steps.length ? (
                  <ol>
                    {recipe.steps.map((step) => (
                      <li key={step.id}>
                        <span className={styles.stepNumber}>{String(step.stepNumber).padStart(2, "0")}</span>
                        <div>
                          <p>{step.instruction}</p>
                          {step.durationMinutes && <small>{t("minutes", { count: step.durationMinutes })}</small>}
                          {step.imageUrl && <Image src={step.imageUrl} alt={t("stepImage", { number: step.stepNumber })} width={640} height={360} unoptimized className={styles.stepImage} />}
                        </div>
                      </li>
                    ))}
                  </ol>
                ) : <p className={styles.emptySection}>{t("noSteps")}</p>}
                {recipe.instructions && (
                  <div className={styles.notes}>
                    <h3>{t("notes")}</h3>
                    <p>{recipe.instructions}</p>
                  </div>
                )}
              </section>
            </div>

            {nutrients.length > 0 && (
              <section className={styles.nutrition} aria-labelledby="recipe-nutrition-title">
                <p className={styles.sectionKicker}>{t("nutritionKicker")}</p>
                <h2 id="recipe-nutrition-title">{t("nutrition")}</h2>
                <dl>
                  {nutrients.map((key) => (
                    <div key={key}>
                      <dt>{t(key)}</dt>
                      <dd>{formatNumber(recipe.nutrition![key]!)} {key === "calories" ? t("calorieUnit") : key === "sodium" ? t("milligramUnit") : t("gramUnit")}</dd>
                    </div>
                  ))}
                </dl>
              </section>
            )}
          </>
        ) : null}
      </div>
    </main>
  );
}
