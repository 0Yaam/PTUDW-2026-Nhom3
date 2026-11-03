"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { RecipeContentFields } from "./recipe-content-fields";
import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useTranslations } from "next-intl";
import type { Category } from "@/components/category-grid";
import { getCategories } from "@/lib/api/categories";
import { getProfile } from "@/lib/api/profile";
import {
  RecipeApiError,
  type RecipeDraft,
  type RecipeDraftInput,
  createRecipeDraft, getRecipeDetail, updateRecipe, changeRecipeStatus,
  type RecipeDetail, type RecipeAction,
} from "@/lib/api/recipes";
import { useAuthStore } from "@/lib/auth-store";
import { focusFirstInvalidField } from "@/lib/form-errors";
import styles from "./recipe-draft-form.module.css";

type FieldErrors = Record<string, string>;
type NutritionField = "calories" | "protein" | "carbohydrates" | "fat" | "fiber" | "sodium";

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

export function RecipeDraftForm({ slug }: { slug?: string }) {
  const router = useRouter();
  const editorT = useTranslations("recipeEditor");
  const busy = useRef(false);
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [editorLoading, setEditorLoading] = useState(Boolean(slug));
  const [refreshRequired, setRefreshRequired] = useState(false);
  const initializedSlug = useRef<string | undefined>(undefined);
  const [editorError, setEditorError] = useState<number | null>(null);
  const [dirty, setDirty] = useState(false);
  const [contentDirty, setContentDirty] = useState<Record<string, boolean>>({});
  const onContentDirty = useCallback((key: string, value: boolean) => setContentDirty((previous) => previous[key] === value ? previous : { ...previous, [key]: value }), []);
  const hasUnsaved = dirty || Object.values(contentDirty).some(Boolean);
  const [message, setMessage] = useState("");
  const [confirmation, setConfirmation] = useState<RecipeAction | null>(null);
  const [formRevision, setFormRevision] = useState(0);
  const t = useTranslations("recipeForm");
  const errorT = useTranslations("errors");
  const session = useAuthStore();
  const accessToken = session?.accessToken;
  const [authorName, setAuthorName] = useState<{ token: string; name: string } | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [categoriesLoading, setCategoriesLoading] = useState(true);
  const [categoriesError, setCategoriesError] = useState(false);
  const [pending, setPending] = useState(false);
  const [formError, setFormError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [createdRecipe, setCreatedRecipe] = useState<RecipeDraft | null>(null);
  const [description, setDescription] = useState("");
  const [instructions, setInstructions] = useState("");
  const [nutritionValues, setNutritionValues] = useState<Record<string, string>>({});
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

  function fillRecipe(detail: RecipeDetail) {
    setRecipe(detail);
    setDescription(detail.description); setInstructions(detail.instructions);
    setNutritionValues(Object.fromEntries(nutritionFields.map((key) => [key, String(detail.nutrition?.[key] ?? "")])));
    setTitle(detail.title); setCategoryId(detail.categoryId);
    setPrepTime(String(detail.prepTimeMinutes)); setCookTime(String(detail.cookTimeMinutes));
    setServings(String(detail.servings)); setDifficulty(String(detail.difficulty));
  }

  useEffect(() => {
    if (!slug || session === undefined) return;
    if (!accessToken) return;
    let active = true;
    void Promise.all([getRecipeDetail(slug, accessToken), getProfile(accessToken)])
      .then(([detail, profile]) => {
        if (!active) return;
        if (!profile.roles.includes("Admin") && (!profile.roles.includes("Author") || profile.id !== detail.authorId)) { setEditorError(403); return; }
        if (initializedSlug.current !== slug) { fillRecipe(detail); initializedSlug.current = slug; }
      })
      .catch((error) => { if (active) setEditorError(error instanceof RecipeApiError ? error.status : 0); })
      .finally(() => { if (active) setEditorLoading(false); });
    return () => { active = false; };
  }, [slug, accessToken, session]);

  useEffect(() => {
    function beforeUnload(event: BeforeUnloadEvent) { if (hasUnsaved || pending) event.preventDefault(); }
    function beforeNavigate(event: MouseEvent) {
      const target = event.target instanceof Element ? event.target.closest("a[href]") : null;
      if (target && !event.defaultPrevented && (hasUnsaved || pending) && !window.confirm(editorT("leaveConfirm"))) { event.preventDefault(); event.stopPropagation(); }
    }
    window.addEventListener("beforeunload", beforeUnload);
    document.addEventListener("click", beforeNavigate, true);
    return () => { window.removeEventListener("beforeunload", beforeUnload); document.removeEventListener("click", beforeNavigate, true); };
  }, [hasUnsaved, pending, editorT]);

  function showError(error: unknown) {
    if (error instanceof RecipeApiError) {
      if (error.status === 401) setFormError(t("sessionExpired"));
      else if (error.status === 409 && error.problem.type === "RECIPE_VERSION_CONFLICT") setFormError(editorT("conflict"));
      else setFormError(problemMessage(error));
    } else setFormError(t("apiUnavailable"));
  }

  async function refreshRecipe() {
    if (!recipe || !accessToken) return;
    const detail = await getRecipeDetail(recipe.slug, accessToken);
    fillRecipe(detail);
    router.refresh();
  }

  async function mutateContent(operation: () => Promise<unknown>): Promise<boolean> {
    if (busy.current || dirty || refreshRequired) return false;
    busy.current = true; setPending(true); setFormError(""); setMessage("");
    try {
      await operation();
      // A committed row must never be submitted twice if the following refresh fails.
      try { await refreshRecipe(); } catch { setFormError(editorT("refreshFailed")); setRefreshRequired(true); }
      setMessage(editorT("saved")); return true;
    } catch (error) {
      showError(error);
      if (!(error instanceof RecipeApiError)) {
        setRefreshRequired(true); setFormError(editorT("unknownSaveResult"));
      }
      return false;
    }
    finally { busy.current = false; setPending(false); }
  }

  async function transition(action: RecipeAction) {
    if (!recipe || !accessToken || busy.current || hasUnsaved || refreshRequired) return;
    busy.current = true; setPending(true); setConfirmation(null); setFormError(""); setMessage("");
    try {
      await changeRecipeStatus(recipe.id, action, accessToken);
      if (action === "delete") { router.replace("/recipes"); router.refresh(); return; }
      try { await refreshRecipe(); } catch { setFormError(editorT("refreshFailed")); setRefreshRequired(true); }
      setMessage(editorT("statusChanged"));
    } catch (error) { showError(error); }
    finally { busy.current = false; setPending(false); }
  }

  async function reloadEditor() {
    if ((hasUnsaved || pending) && !window.confirm(editorT("reloadConfirm"))) return;
    if (!slug || !accessToken || busy.current) return;
    busy.current = true; setPending(true);
    try { fillRecipe(await getRecipeDetail(slug, accessToken)); setDirty(false); setContentDirty({}); setFormRevision((value) => value + 1); setEditorError(null); setRefreshRequired(false); setFormError(""); setFieldErrors({}); setMessage(""); }
    catch (error) { showError(error); }
    finally { busy.current = false; setPending(false); }
  }


  useEffect(() => {
    if (!accessToken) return;
    let active = true;
    void getProfile(accessToken)
      .then((profile) => {
        if (active) setAuthorName({ token: accessToken, name: profile.fullName });
      })
      .catch(() => { /* The saved session name remains the fallback. */ });
    return () => { active = false; };
  }, [accessToken]);

  useEffect(() => {
    let active = true;
    async function loadCategories() {
      setCategoriesLoading(true);
      setCategoriesError(false);
      try {
        const result = await getCategories();
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
    if (!data.get("prepTimeMinutes") || !Number.isSafeInteger(numberValue(data, "prepTimeMinutes")) || numberValue(data, "prepTimeMinutes") <= 0) errors.prepTimeMinutes = t("validation.positive");
    if (!data.get("cookTimeMinutes") || !Number.isSafeInteger(numberValue(data, "cookTimeMinutes")) || numberValue(data, "cookTimeMinutes") < 0) errors.cookTimeMinutes = t("validation.nonNegative");
    if (!data.get("servings") || !Number.isSafeInteger(numberValue(data, "servings")) || numberValue(data, "servings") <= 0) errors.servings = t("validation.positive");

    for (const field of nutritionFields) {
      const value = optionalNumber(data, field);
      if (value !== undefined && (!Number.isFinite(value) || value < 0 || value > 999999.99)) errors[`nutrition.${field}`] = t("validation.nonNegative");
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
    if (!session || busy.current || createdRecipe) return;

    const form = event.currentTarget;
    const data = new FormData(form);
    const errors = validate(data);
    setFieldErrors(errors);
    setFormError("");
    setMessage("");
    if (Object.keys(errors).length > 0) {
      focusFirstInvalidField(form, Object.keys(errors));
      return;
    }

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

    busy.current = true; setPending(true);
    try {
      if (recipe) {
        const updated = await updateRecipe(payload, recipe, session.accessToken);
        setRecipe({ ...recipe, ...updated }); setDirty(false); setMessage(editorT("saved")); router.refresh();
      } else {
        const created = await createRecipeDraft(payload, session.accessToken);
        setCreatedRecipe(created); setDirty(false);
        router.replace(`/recipes/${created.slug}/edit`); router.refresh();
      }
    } catch (error) {
      if (error instanceof RecipeApiError) {
        if (error.status === 401) {
          setFormError(t("sessionExpired"));
          return;
        }
        if (error.status === 422 && error.problem.errors) {
          setFieldErrors(Object.fromEntries(
            Object.entries(error.problem.errors).map(([field, messages]) => [field, messages[0]]),
          ));
          setFormError(t("validationSummary"));
          focusFirstInvalidField(form, Object.keys(error.problem.errors));
          return;
        }
        if (error.status === 409 && !recipe) setFieldErrors({ title: problemMessage(error) });
        showError(error);
      } else {
        setFormError(t("apiUnavailable"));
      }
    } finally {
      busy.current = false; setPending(false);
    }
  }

  function startAnotherRecipe() {
    setCreatedRecipe(null);
    setFieldErrors({});
    setFormError("");
    setTitle(""); setDescription(""); setInstructions(""); setNutritionValues({});
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
            <h1>{slug ? editorT("title") : t("title")}</h1>
            <p className={styles.intro}>{slug ? editorT("description") : t("description")}</p>
          </div>
          <span className={styles.draftBadge}>{recipe ? editorT(`status${recipe.status}`) : t("draft")}</span>
        </header>

        {createdRecipe && (
          <section className={styles.successBanner} aria-live="polite">
            <span aria-hidden="true">✓</span>
            <div><strong>{t("successTitle")}</strong><p>{t("successDescription", { title: createdRecipe.title, slug: createdRecipe.slug })}</p></div>
            <div className={styles.successActions}>
              <Link href={`/recipes/${createdRecipe.slug}`}>{t("manageImages")}</Link>
              <button type="button" onClick={startAnotherRecipe}>{t("createAnother")}</button>
            </div>
          </section>
        )}

        {session === undefined ? (
          <section className={styles.centerState}><p>{t("checkingSession")}</p></section>
        ) : !session ? (
          <section className={styles.centerState}>
            <span aria-hidden="true">✳</span><h2>{t("signInTitle")}</h2><p>{t("signInDescription")}</p>
            <Link className={styles.primaryLink} href="/#auth">{t("signIn")}</Link>
          </section>
        ) : !session.user.roles.some((role) => role === "Author" || role === "Admin") || editorError === 403 ? (
          <section className={styles.centerState}><h2>{editorT("forbidden")}</h2><Link href="/recipes">{editorT("backToRecipes")}</Link></section>
        ) : slug && editorLoading ? (
          <section className={styles.editorSkeleton} aria-busy="true" aria-label={editorT("loading")}><i /><i /><i /></section>
        ) : slug && (editorError !== null || !recipe) ? (
          <section className={styles.centerState}><h2>{editorT(editorError === 404 ? "notFound" : "loadError")}</h2><button type="button" onClick={() => void reloadEditor()}>{editorT("reload")}</button><Link href="/recipes">{editorT("backToRecipes")}</Link></section>
        ) : (
          <div className={styles.workspace}>
            <div className={styles.form}>
            <form id="recipe-base-form" className={styles.form} onSubmit={submit} onChange={() => setDirty(true)} noValidate>
              <fieldset className={styles.baseFields} disabled={pending || refreshRequired || Boolean(createdRecipe)}>
              <section className={styles.section}>
                <div className={styles.sectionHeading}><span>01</span><div><h2>{t("basicTitle")}</h2><p>{t("basicDescription")}</p></div></div>
                <label>{t("recipeTitle")} <b>*</b><input name="title" value={title} onChange={(event) => setTitle(event.target.value)} minLength={5} maxLength={200} aria-invalid={Boolean(fieldErrors.title)} aria-describedby={fieldErrors.title ? "title-error" : undefined} /></label>
                {fieldErrors.title && <p id="title-error" className={styles.fieldError}>{fieldErrors.title}</p>}
                <label>{t("recipeDescription")} <b>*</b><textarea name="description" value={description} onChange={(event) => setDescription(event.target.value)} rows={4} maxLength={2000} aria-invalid={Boolean(fieldErrors.description)} aria-describedby={fieldErrors.description ? "description-error" : undefined} /></label>
                {fieldErrors.description && <p id="description-error" className={styles.fieldError}>{fieldErrors.description}</p>}
                <label>{t("category")} <b>*</b>
                  <select name="categoryId" value={categoryId} onChange={(event) => setCategoryId(event.target.value)} disabled={categoriesLoading || categoriesError} aria-invalid={Boolean(fieldErrors.categoryId)} aria-describedby={fieldErrors.categoryId ? "category-error" : undefined}>
                    <option value="">{categoriesLoading ? t("categoriesLoading") : categoriesError ? t("categoriesUnavailable") : t("categoryPlaceholder")}</option>
                    {categories.map((category) => <option value={category.id} key={category.id}>{category.name}</option>)}
                  </select>
                </label>
                {fieldErrors.categoryId && <p id="category-error" className={styles.fieldError}>{fieldErrors.categoryId}</p>}
                {!categoriesLoading && !categoriesError && categories.length === 0 && <p className={styles.notice}>{t("noCategories")}</p>}
              </section>

              <section className={styles.section}>
                <div className={styles.sectionHeading}><span>02</span><div><h2>{t("timingTitle")}</h2><p>{t("timingDescription")}</p></div></div>
                <div className={styles.numberGrid}>
                  <label>{t("prepTime")} <b>*</b><span className={styles.unitInput}><input name="prepTimeMinutes" type="number" min="1" value={prepTime} onChange={(event) => setPrepTime(event.target.value)} aria-invalid={Boolean(fieldErrors.prepTimeMinutes)} aria-describedby={fieldErrors.prepTimeMinutes ? "prep-time-error" : undefined} /><em>{t("minutes")}</em></span>{fieldErrors.prepTimeMinutes && <small id="prep-time-error">{fieldErrors.prepTimeMinutes}</small>}</label>
                  <label>{t("cookTime")} <b>*</b><span className={styles.unitInput}><input name="cookTimeMinutes" type="number" min="0" value={cookTime} onChange={(event) => setCookTime(event.target.value)} aria-invalid={Boolean(fieldErrors.cookTimeMinutes)} aria-describedby={fieldErrors.cookTimeMinutes ? "cook-time-error" : undefined} /><em>{t("minutes")}</em></span>{fieldErrors.cookTimeMinutes && <small id="cook-time-error">{fieldErrors.cookTimeMinutes}</small>}</label>
                  <label>{t("servings")} <b>*</b><span className={styles.unitInput}><input name="servings" type="number" min="1" value={servings} onChange={(event) => setServings(event.target.value)} aria-invalid={Boolean(fieldErrors.servings)} aria-describedby={fieldErrors.servings ? "servings-error" : undefined} /><em>{t("people")}</em></span>{fieldErrors.servings && <small id="servings-error">{fieldErrors.servings}</small>}</label>
                </div>
                <fieldset className={styles.difficulty}>
                  <legend>{t("difficulty")} <b>*</b></legend>
                  <div>{[1, 2, 3, 4].map((value) => <label className={difficulty === String(value) ? styles.selectedDifficulty : ""} key={value}><input name="difficulty" type="radio" value={value} checked={difficulty === String(value)} onChange={(event) => setDifficulty(event.target.value)} />{t(`difficulty${value}`)}</label>)}</div>
                </fieldset>
              </section>

              <section className={styles.section}>
                <div className={styles.sectionHeading}><span>03</span><div><h2>{t("instructionsTitle")}</h2><p>{t("instructionsDescription")}</p></div></div>
                <label>{t("instructions")}<textarea name="instructions" value={instructions} onChange={(event) => setInstructions(event.target.value)} rows={6} placeholder={t("instructionsPlaceholder")} /></label>
                <p className={styles.notice}>{editorT("createContentHint")}</p>
              </section>

              <section className={styles.section}>
                <button className={styles.nutritionToggle} type="button" aria-expanded={nutritionOpen} onClick={() => setNutritionOpen((open) => !open)}>
                  <span><b>04</b><span><strong>{t("nutritionTitle")}</strong><small>{t("nutritionDescription")}</small></span></span><span aria-hidden="true">{nutritionOpen ? "−" : "+"}</span>
                </button>
                <div hidden={!nutritionOpen} className={styles.nutritionGrid}>{nutritionFields.map((field) => <label key={field}>{t(field)}<span className={styles.unitInput}><input name={field} value={nutritionValues[field] ?? ""} onChange={(event) => setNutritionValues({ ...nutritionValues, [field]: event.target.value })} type="number" min="0" step="0.01" aria-invalid={Boolean(fieldErrors[`nutrition.${field}`])} aria-describedby={fieldErrors[`nutrition.${field}`] ? `nutrition-${field}-error` : undefined} /><em>{field === "calories" ? "kcal" : field === "sodium" ? "mg" : "g"}</em></span>{fieldErrors[`nutrition.${field}`] && <small id={`nutrition-${field}-error`}>{fieldErrors[`nutrition.${field}`]}</small>}</label>)}</div>
              </section>
              </fieldset>
            </form>
            {recipe && accessToken && <RecipeContentFields key={formRevision} recipe={recipe} accessToken={accessToken} disabled={pending || dirty || refreshRequired} onDirty={onContentDirty} mutate={mutateContent} />}
            </div>

            <aside className={styles.summary}>
              <p className={styles.summaryEyebrow}>{t("summaryEyebrow")}</p>
              <h2>{title.trim() || t("untitled")}</h2>
              <dl>
                <div><dt>{t("category")}</dt><dd>{selectedCategory?.name ?? "—"}</dd></div>
                <div><dt>{t("totalTime")}</dt><dd>{totalTime} {t("minutes")}</dd></div>
                <div><dt>{t("servings")}</dt><dd>{servings || "—"} {t("people")}</dd></div>
                <div><dt>{t("difficulty")}</dt><dd>{t(`difficulty${difficulty}`)}</dd></div>
              </dl>
              <div className={styles.privacy}><span aria-hidden="true">⌁</span><p><strong>{recipe ? editorT(`status${recipe.status}`) : t("privateTitle")}</strong><br />{recipe ? editorT(`visibility${recipe.status}`) : t("privateDescription")}</p></div>
              {message && <p role="status" className={styles.notice}>{message}</p>}
              {formError && <p className={styles.formError} role="alert">{formError}</p>}
              {hasUnsaved && <p className={styles.notice}>{editorT("unsaved")}</p>}
              {slug && <button type="button" className={styles.secondaryButton} disabled={pending} onClick={() => void reloadEditor()}>{editorT("reload")}</button>}
              <button className={styles.submit} type="button" disabled={pending || refreshRequired || Boolean(createdRecipe) || categoriesLoading || categoriesError || categories.length === 0} onClick={() => (document.getElementById("recipe-base-form") as HTMLFormElement | null)?.requestSubmit()}>{pending ? t("saving") : recipe ? editorT("saveChanges") : t("save")}</button>
              {recipe && <div className={styles.lifecycle}>
                <Link href={`/recipes/${recipe.slug}`}>{editorT("viewRecipe")}</Link>
                <p>{editorT("publishHint")}</p>
                {recipe.status !== "Archived" && <button type="button" disabled={pending || refreshRequired || hasUnsaved || (recipe.status === "Draft" && (!recipe.ingredients.length || !recipe.steps.length))} onClick={() => void transition(recipe.status === "Published" ? "unpublish" : "publish")}>{editorT(recipe.status === "Published" ? "unpublish" : "publish")}</button>}
                {recipe.status !== "Archived" && <button type="button" disabled={pending || refreshRequired || hasUnsaved} onClick={() => setConfirmation("archive")}>{editorT("archive")}</button>}
                {recipe.status === "Archived" && <p>{editorT("archivedHint")}</p>}
                <button type="button" className={styles.dangerButton} disabled={pending || refreshRequired || hasUnsaved} onClick={() => setConfirmation("delete")}>{editorT("delete")}</button>
                {confirmation && <div role="group" aria-label={editorT("confirmation")} className={styles.confirmation}><p>{editorT(confirmation === "delete" ? "deleteConfirm" : "archiveConfirm", { title: recipe.title })}</p><button type="button" disabled={pending || refreshRequired || hasUnsaved} onClick={() => void transition(confirmation)}>{editorT("confirm")}</button><button type="button" onClick={() => setConfirmation(null)}>{editorT("cancel")}</button></div>}
              </div>}
              <p className={styles.submitHint}>{recipe ? editorT("savedOwner", { name: recipe.author.fullName }) : t("saveHint", { name: authorName?.token === session.accessToken ? authorName.name : session.user.fullName })}</p>
            </aside>
          </div>
        )}
      </div>
    </main>
  );
}
