"use client";

import Link from "next/link";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import type { Category } from "@/components/category-grid";
import {
  RecipeApiError,
  type RecipeDraft,
  type RecipeDraftInput,
  createRecipeDraft,
} from "@/lib/api/recipes";
import {
  AUTH_SESSION_CHANGED,
  clearAuthSession,
  loadAuthSession,
  type AuthSession,
} from "@/lib/auth-session";
import styles from "./recipe-draft-form.module.css";

type FieldErrors = Record<string, string>;
type NutritionField = "calories" | "protein" | "carbohydrates" | "fat" | "fiber" | "sodium";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const nutritionFields: NutritionField[] = [
  "calories",
  "protein",
  "carbohydrates",
  "fat",
  "fiber",
  "sodium",
];

function numberValue(data: FormData, field: string): number {
  return Number(data.get(field));
}

function optionalNumber(data: FormData, field: NutritionField): number | undefined {
  const value = data.get(field)?.toString().trim();
  return value ? Number(value) : undefined;
}

export function RecipeDraftForm() {
  const t = useTranslations("recipeForm");
  const errorT = useTranslations("errors");
  const [session, setSession] = useState<AuthSession | null | undefined>(undefined);
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [categoriesError, setCategoriesError] = useState(false);
  const [pending, setPending] = useState(false);
  const [formError, setFormError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [createdRecipe, setCreatedRecipe] = useState<RecipeDraft | null>(null);
  const [title, setTitle] = useState("");
  const [categoryId, setCategoryId] = useState("");
  const [prepTime, setPrepTime] = useState("20");
  const [cookTime, setCookTime] = useState("0");
  const [servings, setServings] = useState("4");
  const [difficulty, setDifficulty] = useState("1");
  const [nutritionOpen, setNutritionOpen] = useState(false);

  const selectedCategory = useMemo(
    () => categories.find((category) => category.id === categoryId),
    [categories, categoryId],
  );
  const totalTime = Math.max(0, Number(prepTime) || 0) + Math.max(0, Number(cookTime) || 0);

  useEffect(() => {
    const updateSession = () => setSession(loadAuthSession());
    updateSession();
    window.addEventListener(AUTH_SESSION_CHANGED, updateSession);
    return () => window.removeEventListener(AUTH_SESSION_CHANGED, updateSession);
  }, []);

  useEffect(() => {
    let active = true;
    async function loadCategories() {
      setCategoriesLoading(true);
      setCategoriesError(false);
      try {
        const response = await fetch(`${apiUrl}/api/v1/categories`, { cache: "no-store" });
        if (!response.ok) throw new Error("categories");
        const result = (await response.json()) as Category[];
        if (active) setCategories(result);
      } catch {
        if (active) setCategoriesError(true);
      } finally {
        if (active) setCategoriesLoading(false);
      }
    }
    void loadCategories();
    return () => { active = false; };
  }, []);

  function validate(data: FormData): FieldErrors {
    const errors: FieldErrors = {};
    const recipeTitle = data.get("title")?.toString().trim() ?? "";
    const description = data.get("description")?.toString().trim() ?? "";
    if (recipeTitle.length < 5 || recipeTitle.length > 200) errors.title = t("validation.title");
    if (!description || description.length > 2000) errors.description = t("validation.description");
    if (!data.get("categoryId")) errors.categoryId = t("validation.category");
    if (numberValue(data, "prepTimeMinutes") <= 0) errors.prepTimeMinutes = t("validation.positive");
    if (numberValue(data, "cookTimeMinutes") < 0) errors.cookTimeMinutes = t("validation.nonNegative");
    if (numberValue(data, "servings") <= 0) errors.servings = t("validation.positive");

    for (const field of nutritionFields) {
      const value = optionalNumber(data, field);
      if (value !== undefined && value < 0) errors[`nutrition.${field}`] = t("validation.nonNegative");
    }
    return errors;
  }

  function problemMessage(error: RecipeApiError): string {
    const type = error.problem.type;
    if (type && errorT.has(type)) return errorT(type);
    return error.problem.detail ?? t("requestFailed");
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;

    const form = event.currentTarget;
    const data = new FormData(form);
    const errors = validate(data);
    setFieldErrors(errors);
    setFormError("");
    setCreatedRecipe(null);
    if (Object.keys(errors).length > 0) return;

    const nutrition = Object.fromEntries(
      nutritionFields.flatMap((field) => {
        const value = optionalNumber(data, field);
        return value === undefined ? [] : [[field, value]];
      }),
    ) as RecipeDraftInput["nutrition"];

    const payload: RecipeDraftInput = {
      title: data.get("title")?.toString().trim() ?? "",
      description: data.get("description")?.toString().trim() ?? "",
      categoryId: data.get("categoryId")?.toString() ?? "",
      prepTimeMinutes: numberValue(data, "prepTimeMinutes"),
      cookTimeMinutes: numberValue(data, "cookTimeMinutes"),
      servings: numberValue(data, "servings"),
      difficulty: numberValue(data, "difficulty"),
      instructions: data.get("instructions")?.toString().trim() ?? "",
      ...(nutrition && Object.keys(nutrition).length > 0 ? { nutrition } : {}),
    };

    setPending(true);
    try {
      setCreatedRecipe(await createRecipeDraft(payload, session.accessToken));
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      if (error instanceof RecipeApiError) {
        if (error.status === 401) {
          clearAuthSession();
          setFormError(t("sessionExpired"));
          return;
        }
        if (error.status === 422 && error.problem.errors) {
          setFieldErrors(Object.fromEntries(
            Object.entries(error.problem.errors).map(([field, messages]) => [field, messages[0]]),
          ));
          setFormError(t("validationSummary"));
          return;
        }
        if (error.status === 409) setFieldErrors({ title: problemMessage(error) });
        setFormError(problemMessage(error));
      } else {
        setFormError(t("apiUnavailable"));
      }
    } finally {
      setPending(false);
    }
  }

  function startAnotherRecipe() {
    setCreatedRecipe(null);
    setFieldErrors({});
    setFormError("");
    setTitle("");
    setCategoryId("");
    setPrepTime("20");
    setCookTime("0");
    setServings("4");
    setDifficulty("1");
  }

  return (
    <main id="main-content" className={styles.page}>
      <div className={styles.shell}>
        <header className={styles.pageHeader}>
          <div>
            <Link className={styles.backLink} href="/">← {t("back")}</Link>
            <p className={styles.eyebrow}>{t("eyebrow")}</p>
            <h1>{t("title")}</h1>
            <p className={styles.intro}>{t("description")}</p>
          </div>
          <span className={styles.draftBadge}>{t("draft")}</span>
        </header>

        {createdRecipe && (
          <section className={styles.successBanner} aria-live="polite">
            <span aria-hidden="true">✓</span>
            <div><strong>{t("successTitle")}</strong><p>{t("successDescription", { title: createdRecipe.title, slug: createdRecipe.slug })}</p></div>
            <button type="button" onClick={startAnotherRecipe}>{t("createAnother")}</button>
          </section>
        )}

        {session === undefined ? (
          <section className={styles.centerState}><p>{t("checkingSession")}</p></section>
        ) : !session ? (
          <section className={styles.centerState}>
            <span aria-hidden="true">✳</span><h2>{t("signInTitle")}</h2><p>{t("signInDescription")}</p>
            <Link className={styles.primaryLink} href="/#auth">{t("signIn")}</Link>
          </section>
        ) : (
          <div className={styles.workspace}>
            <form className={styles.form} onSubmit={submit} noValidate>
              <section className={styles.section}>
                <div className={styles.sectionHeading}><span>01</span><div><h2>{t("basicTitle")}</h2><p>{t("basicDescription")}</p></div></div>
                <label>{t("recipeTitle")} <b>*</b><input name="title" value={title} onChange={(event) => setTitle(event.target.value)} minLength={5} maxLength={200} aria-invalid={Boolean(fieldErrors.title)} /></label>
                {fieldErrors.title && <p className={styles.fieldError}>{fieldErrors.title}</p>}
                <label>{t("recipeDescription")} <b>*</b><textarea name="description" rows={4} maxLength={2000} aria-invalid={Boolean(fieldErrors.description)} /></label>
                {fieldErrors.description && <p className={styles.fieldError}>{fieldErrors.description}</p>}
                <label>{t("category")} <b>*</b>
                  <select name="categoryId" value={categoryId} onChange={(event) => setCategoryId(event.target.value)} disabled={categoriesLoading || categoriesError} aria-invalid={Boolean(fieldErrors.categoryId)}>
                    <option value="">{categoriesLoading ? t("categoriesLoading") : categoriesError ? t("categoriesUnavailable") : t("categoryPlaceholder")}</option>
                    {categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}
                  </select>
                </label>
                {fieldErrors.categoryId && <p className={styles.fieldError}>{fieldErrors.categoryId}</p>}
                {!categoriesLoading && !categoriesError && categories.length === 0 && <p className={styles.notice}>{t("noCategories")}</p>}
              </section>

              <section className={styles.section}>
                <div className={styles.sectionHeading}><span>02</span><div><h2>{t("timingTitle")}</h2><p>{t("timingDescription")}</p></div></div>
                <div className={styles.numberGrid}>
                  <label>{t("prepTime")} <b>*</b><span className={styles.unitInput}><input name="prepTimeMinutes" type="number" min="1" value={prepTime} onChange={(event) => setPrepTime(event.target.value)} aria-invalid={Boolean(fieldErrors.prepTimeMinutes)} /><em>{t("minutes")}</em></span>{fieldErrors.prepTimeMinutes && <small>{fieldErrors.prepTimeMinutes}</small>}</label>
                  <label>{t("cookTime")} <b>*</b><span className={styles.unitInput}><input name="cookTimeMinutes" type="number" min="0" value={cookTime} onChange={(event) => setCookTime(event.target.value)} aria-invalid={Boolean(fieldErrors.cookTimeMinutes)} /><em>{t("minutes")}</em></span>{fieldErrors.cookTimeMinutes && <small>{fieldErrors.cookTimeMinutes}</small>}</label>
                  <label>{t("servings")} <b>*</b><span className={styles.unitInput}><input name="servings" type="number" min="1" value={servings} onChange={(event) => setServings(event.target.value)} aria-invalid={Boolean(fieldErrors.servings)} /><em>{t("people")}</em></span>{fieldErrors.servings && <small>{fieldErrors.servings}</small>}</label>
                </div>
                <fieldset className={styles.difficulty}>
                  <legend>{t("difficulty")} <b>*</b></legend>
                  <div>{[1, 2, 3, 4].map((value) => <label className={difficulty === String(value) ? styles.selectedDifficulty : ""} key={value}><input name="difficulty" type="radio" value={value} checked={difficulty === String(value)} onChange={(event) => setDifficulty(event.target.value)} />{t(`difficulty${value}`)}</label>)}</div>
                </fieldset>
              </section>

              <section className={styles.section}>
                <div className={styles.sectionHeading}><span>03</span><div><h2>{t("instructionsTitle")}</h2><p>{t("instructionsDescription")}</p></div></div>
                <label>{t("instructions")}<textarea name="instructions" rows={6} placeholder={t("instructionsPlaceholder")} /></label>
                <p className={styles.notice}>{t("deferredScope")}</p>
              </section>

              <section className={styles.section}>
                <button className={styles.nutritionToggle} type="button" aria-expanded={nutritionOpen} onClick={() => setNutritionOpen((open) => !open)}>
                  <span><b>04</b><span><strong>{t("nutritionTitle")}</strong><small>{t("nutritionDescription")}</small></span></span><span aria-hidden="true">{nutritionOpen ? "−" : "+"}</span>
                </button>
                {nutritionOpen && <div className={styles.nutritionGrid}>{nutritionFields.map((field) => <label key={field}>{t(field)}<span className={styles.unitInput}><input name={field} type="number" min="0" step="0.01" aria-invalid={Boolean(fieldErrors[`nutrition.${field}`])} /><em>{field === "calories" ? "kcal" : field === "sodium" ? "mg" : "g"}</em></span>{fieldErrors[`nutrition.${field}`] && <small>{fieldErrors[`nutrition.${field}`]}</small>}</label>)}</div>}
              </section>
            </form>

            <aside className={styles.summary}>
              <p className={styles.summaryEyebrow}>{t("summaryEyebrow")}</p>
              <h2>{title.trim() || t("untitled")}</h2>
              <dl>
                <div><dt>{t("category")}</dt><dd>{selectedCategory?.name ?? "—"}</dd></div>
                <div><dt>{t("totalTime")}</dt><dd>{totalTime} {t("minutes")}</dd></div>
                <div><dt>{t("servings")}</dt><dd>{servings || "—"} {t("people")}</dd></div>
                <div><dt>{t("difficulty")}</dt><dd>{t(`difficulty${difficulty}`)}</dd></div>
              </dl>
              <div className={styles.privacy}><span aria-hidden="true">⌁</span><p><strong>{t("privateTitle")}</strong><br />{t("privateDescription")}</p></div>
              {formError && <p className={styles.formError} role="alert">{formError}</p>}
              <button className={styles.submit} type="button" disabled={pending || categoriesLoading || categoriesError || categories.length === 0} onClick={() => document.querySelector<HTMLFormElement>(`.${styles.form}`)?.requestSubmit()}>{pending ? t("saving") : t("save")}</button>
              <p className={styles.submitHint}>{t("saveHint", { name: session.user.fullName })}</p>
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}
