"use client";

import { FormEvent, useCallback, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { useLocale, useTranslations } from "next-intl";
import type { Category } from "@/components/category-grid";
import { LocaleSwitcher } from "@/components/locale-switcher";
import styles from "./page.module.css";

type Problem = { type?: string; detail?: string; errors?: Record<string, string[]> };
type LoginResponse = { accessToken: string; user: { fullName: string; roles: string[] } };
type Overview = {
  users: number; categories: number; images: number;
  recipes: { total: number; draft: number; published: number; archived: number };
  jobs: Record<"email" | "resize" | "cleanup", { pending: number; failed: number }>;
  recentRecipes: { id: string; title: string; status: string; author: string; createdAt: string }[];
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type IconName = "spark" | "grid" | "book" | "post" | "image" | "users" | "chat" | "chart" | "settings" | "external" | "search" | "plus" | "list" | "link";

const iconPaths: Record<IconName, string> = {
  spark: "M12 2 14.2 9.8 22 12l-7.8 2.2L12 22l-2.2-7.8L2 12l7.8-2.2L12 2Z",
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  book: "M4 4h12a3 3 0 0 1 3 3v13H7a3 3 0 0 0-3 1V4Zm0 13a3 3 0 0 1 3-1h12",
  post: "M6 3h12l3 3v15H6V3Zm4 6h7m-7 4h7m-7 4h5",
  image: "M4 4h16v16H4zM8 9h.01M4 17l5-5 3 3 2-2 6 6",
  users: "M16 20v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2h14ZM9 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm13 10v-2a4 4 0 0 0-3-3.87M16 4.13a3 3 0 0 1 0 5.74",
  chat: "M4 4h16v12H8l-4 4V4Zm4 4h8m-8 4h6",
  chart: "M4 20V4m0 16h16M8 16l4-5 3 2 5-7",
  settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0-6v3m0 14v3M4.9 4.9 7 7m10 10 2.1 2.1M2 12h3m14 0h3M4.9 19.1 7 17M17 7l2.1-2.1",
  external: "M13 4h7v7m0-7-9 9M20 14v6H4V4h6",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm5-2 5 5",
  plus: "M12 4v16M4 12h16",
  list: "M4 5h16M4 12h16M4 19h16",
  link: "M10 13a5 5 0 0 0 7 0l3-3a5 5 0 0 0-7-7l-2 2m3 6a5 5 0 0 0-7 0l-3 3a5 5 0 0 0 7 7l2-2",
};

function AdminIcon({ name }: { name: IconName }) {
  return <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"><path d={iconPaths[name]} /></svg>;
}

function normalizeSlug(value: string): string {
  return value
    .replace(/[đĐ]/g, "d")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
}

export default function ManageCategories() {
  const t = useTranslations("admin");
  const errors = useTranslations("errors");
  const locale = useLocale();
  const [categories, setCategories] = useState<Category[]>([]);
  const [token, setToken] = useState("");
  const [adminName, setAdminName] = useState("");
  const [selected, setSelected] = useState<Category | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [slug, setSlug] = useState("");
  const [editSlug, setEditSlug] = useState(false);
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Record<string, string[]>>({});
  const [overview, setOverview] = useState<Overview | null>(null);
  const [overviewLoading, setOverviewLoading] = useState(false);
  const [overviewError, setOverviewError] = useState(false);
  const errorRef = useRef<HTMLParagraphElement>(null);

  useEffect(() => { if (error) errorRef.current?.focus(); }, [error]);

  const loadOverview = useCallback(async (accessToken: string) => {
    setOverviewLoading(true);
    setOverviewError(false);
    try {
      const response = await fetch(`${apiUrl}/api/v1/admin/overview`, {
        headers: { Authorization: `Bearer ${accessToken}` }, cache: "no-store",
      });
      if (!response.ok) throw new Error("overview");
      setOverview((await response.json()) as Overview);
    } catch {
      setOverviewError(true);
    } finally {
      setOverviewLoading(false);
    }
  }, []);

  const recipeTotal = useMemo(
    () => categories.reduce((sum, category) => sum + category.recipe_count, 0),
    [categories],
  );
  const filteredCategories = useMemo(() => {
    const query = search.trim().toLocaleLowerCase();
    if (!query) return categories;
    return categories.filter((category) =>
      [category.name, category.slug, category.description ?? ""]
        .some((value) => value.toLocaleLowerCase().includes(query)),
    );
  }, [categories, search]);
  const topCategories = useMemo(
    () => [...categories].sort((a, b) => b.recipe_count - a.recipe_count).slice(0, 5),
    [categories],
  );

  function problemText(problem: Problem): string {
    const fieldError = Object.values(problem.errors ?? {}).flat()[0];
    if (problem.type && errors.has(problem.type)) return errors(problem.type);
    return fieldError ?? problem.detail ?? errors("fallback");
  }

  const loadCategories = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/categories`, { cache: "no-store" });
      if (!response.ok) throw new Error("load");
      setCategories((await response.json()) as Category[]);
    } catch {
      setError(t("loadFailed"));
    } finally {
      setLoading(false);
    }
  }, [t]);

  useEffect(() => {
    let active = true;
    void fetch(`${apiUrl}/api/v1/categories`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("load");
        return response.json() as Promise<Category[]>;
      })
      .then((items) => { if (active) setCategories(items); })
      .catch(() => { if (active) setError(t("loadFailed")); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [t]);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setFieldErrors({});
    setMessage("");
    setBusy(true);
    const form = event.currentTarget;
    const data = new FormData(form);
    try {
      const response = await fetch(`${apiUrl}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: data.get("email"), password: data.get("password") }),
      });
      if (!response.ok) {
        setError(problemText((await response.json()) as Problem));
        return;
      }
      const result = (await response.json()) as LoginResponse;
      if (!result.user.roles.includes("Admin")) {
        setError(t("notAdmin"));
        return;
      }
      setToken(result.accessToken);
      setAdminName(result.user.fullName);
      void loadOverview(result.accessToken);
      form.reset();
    } catch {
      setError(t("apiUnavailable"));
    } finally {
      setBusy(false);
    }
  }

  function choose(category: Category | null) {
    setSelected(category);
    setName(category?.name ?? "");
    setDescription(category?.description ?? "");
    setSlug(category?.slug ?? "");
    setEditSlug(false);
    setConfirmDelete(false);
    setError("");
    setMessage("");
    setFieldErrors({});
  }

  function signOut() {
    setToken("");
    setAdminName("");
    setOverview(null);
    choose(null);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setFieldErrors({});
    setBusy(true);
    try {
      const payload: { name: string; description: string | null; slug?: string } = {
        name,
        description: description || null,
      };
      if (selected && editSlug) payload.slug = slug;
      const response = await fetch(
        selected ? `${apiUrl}/api/v1/categories/${selected.id}` : `${apiUrl}/api/v1/categories`,
        {
          method: selected ? "PUT" : "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify(payload),
        },
      );
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          signOut();
          setError(t(response.status === 403 ? "notAdmin" : "sessionExpired"));
        } else {
          const problem = (await response.json()) as Problem;
          setFieldErrors(problem.errors ?? {});
          setError(problemText(problem));
        }
        return;
      }
      const saved = (await response.json()) as Category;
      const slugChanged = Boolean(selected && saved.slug !== selected.slug);
      setMessage(selected ? t(slugChanged ? "updatedSlug" : "updated") : t("created"));
      setSelected(saved);
      setName(saved.name);
      setDescription(saved.description ?? "");
      setSlug(saved.slug);
      setEditSlug(false);
      setConfirmDelete(false);
      await loadCategories();
      void loadOverview(token);
    } catch {
      setError(t("apiUnavailable"));
    } finally {
      setBusy(false);
    }
  }

  async function removeSelected() {
    if (!selected) return;
    const deletedName = selected.name;
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const response = await fetch(`${apiUrl}/api/v1/categories/${selected.id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          signOut();
          setError(t(response.status === 403 ? "notAdmin" : "sessionExpired"));
        } else {
          setError(problemText((await response.json()) as Problem));
        }
        return;
      }
      setSelected(null);
      setName("");
      setDescription("");
      setSlug("");
      setEditSlug(false);
      setConfirmDelete(false);
      setMessage(t("deleted", { name: deletedName }));
      await loadCategories();
      void loadOverview(token);
    } catch {
      setError(t("apiUnavailable"));
    } finally {
      setBusy(false);
    }
  }

  if (!token) {
    return (
      <main id="main-content" className={styles.loginShell}>
        <section className={styles.loginBrand}>
          <Link className={styles.brand} href="/"><span><AdminIcon name="spark" /></span>{t("brand")}</Link>
          <blockquote>{t("loginQuote")}</blockquote>
        </section>
        <section className={styles.loginCard} aria-labelledby="admin-login">
          <div className={styles.loginToolbar}><Link href="/">← {t("visitSite")}</Link><LocaleSwitcher compact /></div>
          <p className={styles.kicker}>{t("access")}</p>
          <h1 id="admin-login">{t("loginTitle")}</h1>
          <p className={styles.muted}>{t("loginDescription")}</p>
          <form onSubmit={signIn} className={styles.form}>
            <label>{t("email")}<input name="email" type="email" autoComplete="email" required /></label>
            <label>{t("password")}<input name="password" type="password" autoComplete="current-password" required /></label>
            <button type="submit" disabled={busy}>{busy ? t("signingIn") : t("signIn")}</button>
          </form>
          <p className={styles.help}>{t("newHere")} <Link href="/#auth">{t("registerLink")}</Link>. {t("roleHint")}</p>
          {error && <p role="alert" className={styles.error}>{error}</p>}
        </section>
      </main>
    );
  }

  return (
    <main id="main-content" className={styles.dashboard}>
      <aside className={styles.sidebar}>
        <Link className={styles.brand} href="/"><span><AdminIcon name="spark" /></span>{t("brand")}</Link>
        <p className={styles.navLabel}>{t("workspace")}</p>
        <nav aria-label={t("workspace")}>
          <a className={styles.navItem} href="#overview"><AdminIcon name="grid" />{t("navOverview")}</a>
        </nav>
        <p className={styles.navLabel}>{t("content")}</p>
        <nav aria-label={t("content")}>
          <a className={styles.navItemActive} href="#category-list"><AdminIcon name="list" />{t("categories")}</a>
          <div className={styles.navItemDisabled} aria-disabled="true"><AdminIcon name="book" />{t("navRecipes")}<small>{t("comingSoon")}</small></div>
          <div className={styles.navItemDisabled} aria-disabled="true"><AdminIcon name="post" />{t("navPosts")}<small>{t("comingSoon")}</small></div>
          <div className={styles.navItemDisabled} aria-disabled="true"><AdminIcon name="image" />{t("navMedia")}<small>{t("comingSoon")}</small></div>
        </nav>
        <p className={styles.navLabel}>{t("management")}</p>
        <nav aria-label={t("management")}>
          <div className={styles.navItemDisabled} aria-disabled="true"><AdminIcon name="users" />{t("navUsers")}<small>{t("comingSoon")}</small></div>
          <div className={styles.navItemDisabled} aria-disabled="true"><AdminIcon name="chat" />{t("navComments")}<small>{t("comingSoon")}</small></div>
          <div className={styles.navItemDisabled} aria-disabled="true"><AdminIcon name="chart" />{t("navAnalytics")}<small>{t("comingSoon")}</small></div>
        </nav>
        <p className={styles.navLabel}>{t("system")}</p>
        <nav aria-label={t("system")}>
          <div className={styles.navItemDisabled} aria-disabled="true"><AdminIcon name="settings" />{t("navSettings")}<small>{t("comingSoon")}</small></div>
          <Link className={styles.navItem} href="/"><AdminIcon name="external" />{t("visitSite")}</Link>
        </nav>
        <div className={styles.sidebarAccount}>
          <span className={styles.avatar} aria-hidden="true">{adminName.slice(0, 1).toUpperCase()}</span>
          <div><strong>{adminName}</strong><small>{t("signedInAs")}</small></div>
          <button type="button" onClick={signOut}>{t("signOut")}</button>
        </div>
      </aside>

      <div className={styles.content}>
        <header className={styles.topbar}>
          <span className={styles.mobileBrand}><AdminIcon name="spark" /></span>
          <span>{t("breadcrumb")}</span>
          <div className={styles.activeModule}><i aria-hidden="true" />{t("activeModule")}</div>
          <LocaleSwitcher compact />
          <button className={styles.mobileSignOut} type="button" onClick={signOut}>{t("signOut")}</button>
        </header>
        <div className={styles.page}>
          <section id="overview" className={styles.overview} aria-labelledby="overview-title">
            <div className={styles.overviewHeading}>
              <div><p className={styles.kicker}>{t("overviewEyebrow")}</p><h1 id="overview-title">{t("overviewTitle")}</h1><p>{t("overviewSubtitle")}</p></div>
              <button type="button" onClick={() => void loadOverview(token)} disabled={overviewLoading}>{t("refreshOverview")}</button>
            </div>
            {overviewError && <p role="alert" className={styles.error}>{t("overviewError")}</p>}
            {overviewLoading && !overview && <p role="status" className={styles.state}>{t("overviewLoading")}</p>}
            {overview && <>
              <div className={styles.overviewStats}>
                <article><span>{t("overviewUsers")}</span><strong>{overview.users}</strong><small>{t("overviewUsersHint")}</small></article>
                <article><span>{t("overviewRecipes")}</span><strong>{overview.recipes.total}</strong><small>{t("overviewRecipesHint")}</small></article>
                <article><span>{t("overviewCategories")}</span><strong>{overview.categories}</strong><small>{t("overviewCategoriesHint")}</small></article>
                <article><span>{t("overviewImages")}</span><strong>{overview.images}</strong><small>{t("overviewImagesHint")}</small></article>
              </div>
              <div className={styles.overviewGrid}>
                <article className={styles.overviewPanel}>
                  <h2>{t("recipeStatusTitle")}</h2><p>{t("recipeStatusHint")}</p>
                  {(["published", "draft", "archived"] as const).map((status) => <div className={styles.statusRow} key={status}>
                    <div><span>{t(`recipeStatus${status}`)}</span><strong>{overview.recipes[status]}</strong></div>
                    <progress max={Math.max(overview.recipes.total, 1)} value={overview.recipes[status]} aria-label={t(`recipeStatus${status}`)} />
                  </div>)}
                </article>
                <article className={styles.overviewPanel}>
                  <h2>{t("jobsTitle")}</h2><p>{t("jobsHint")}</p>
                  {(["email", "resize", "cleanup"] as const).map((kind) => <div className={styles.jobRow} key={kind}>
                    <span>{t(`job${kind}`)}</span><span>{t("jobPending")}: <strong>{overview.jobs[kind].pending}</strong></span><span className={overview.jobs[kind].failed ? styles.jobFailed : ""}>{t("jobFailed")}: <strong>{overview.jobs[kind].failed}</strong></span>
                  </div>)}
                </article>
              </div>
              <article className={styles.overviewPanel}>
                <h2>{t("recentTitle")}</h2><p>{t("recentHint")}</p>
                {overview.recentRecipes.length === 0 ? <p className={styles.muted}>{t("recentEmpty")}</p> : <div className={styles.recentList}>
                  {overview.recentRecipes.map((recipe) => <div key={recipe.id}><strong>{recipe.title}</strong><span>{recipe.author}</span><small>{t(`recipeStatus${recipe.status.toLowerCase()}`)}</small><time dateTime={recipe.createdAt}>{new Date(recipe.createdAt).toLocaleDateString(locale)}</time></div>)}
                </div>}
              </article>
              <article className={styles.overviewPanel}>
                <h2>{t("topCategoriesTitle")}</h2><p>{t("topCategoriesHint")}</p>
                {topCategories.length === 0 ? <p className={styles.muted}>{t("topCategoriesEmpty")}</p> : <div className={styles.categoryRanking}>
                  {topCategories.map((category, index) => <div key={category.id}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <strong>{category.name}</strong>
                    <progress max={Math.max(topCategories[0].recipe_count, 1)} value={category.recipe_count} aria-label={category.name} />
                    <small>{category.recipe_count}</small>
                  </div>)}
                </div>}
              </article>
            </>}
          </section>
          <div className={styles.pageHead}>
            <div><p className={styles.kicker}>{t("breadcrumb")}</p><h1>{t("title")}</h1><p>{t("subtitle")}</p></div>
            <button className={styles.primaryButton} type="button" onClick={() => choose(null)}><AdminIcon name="plus" />{t("new")}</button>
          </div>

          <section className={styles.stats} aria-label={t("title")}>
            <article><span className={styles.statIcon}><AdminIcon name="list" /></span><div><p>{t("totalCategories")}</p><strong>{categories.length}</strong></div></article>
            <article><span className={styles.statIcon}><AdminIcon name="book" /></span><div><p>{t("totalRecipes")}</p><strong>{recipeTotal}</strong></div></article>
            <article><span className={styles.statIcon}><AdminIcon name="link" /></span><div><p>{t("stableSlugs")}</p><strong>{categories.length}</strong></div></article>
          </section>

          <div className={styles.workspace}>
            <section id="category-list" className={styles.tablePanel} aria-labelledby="list-title">
              <div className={styles.panelHead}>
                <div><h2 id="list-title">{t("listTitle")}</h2><p>{t("listHint")}</p></div>
                <label className={styles.searchBox}><AdminIcon name="search" /><span className={styles.srOnly}>{t("search")}</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("searchPlaceholder")} /></label>
              </div>
              {loading ? <p className={styles.state}>{t("loading")}</p> : categories.length === 0 ? <p className={styles.state}>{t("empty")}</p> : (
                filteredCategories.length === 0 ? <p className={styles.state}>{t("noResults")}</p> : <div className={styles.tableScroll}><table>
                  <thead><tr><th>{t("tableName")}</th><th>{t("tableSlug")}</th><th>{t("tableRecipes")}</th><th><span className={styles.srOnly}>{t("tableAction")}</span></th></tr></thead>
                  <tbody>{filteredCategories.map((category) => (
                    <tr key={category.id} className={selected?.id === category.id ? styles.selectedRow : ""}>
                      <td><strong>{category.name}</strong><small>{category.description ?? "—"}</small></td>
                      <td><code>/{category.slug}</code></td><td><span className={styles.mobileRecipeCount}>{t("tableRecipes")}: </span>{category.recipe_count}</td>
                      <td><button type="button" className={styles.editButton} onClick={() => choose(category)}>{t("edit")}</button></td>
                    </tr>
                  ))}</tbody>
                </table></div>
              )}
            </section>

            <section className={styles.editor} aria-labelledby="editor-title">
              <p className={styles.kicker}>{selected ? t("editKicker") : t("createKicker")}</p>
              <h2 id="editor-title">{selected ? t("editTitle") : t("createTitle")}</h2>
              <p className={styles.muted}>{t("formHint")}</p>
              <form onSubmit={save} className={styles.form}>
                {error && <p ref={errorRef} tabIndex={-1} role="alert" className={styles.error}>{error}</p>}
                {message && <p role="status" className={styles.success}>{message}</p>}
                <label htmlFor="category-name">{t("name")}</label><input id="category-name" value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={50} required aria-invalid={Boolean(fieldErrors.name)} aria-describedby={fieldErrors.name ? "category-name-error" : undefined} />
                {fieldErrors.name && <small id="category-name-error" className={styles.fieldError}>{t("nameInvalid")}</small>}
                <label htmlFor="category-description">{t("description")}</label><textarea id="category-description" value={description} onChange={(event) => setDescription(event.target.value)} placeholder={t("descriptionPlaceholder")} rows={5} aria-invalid={Boolean(fieldErrors.description)} aria-describedby={fieldErrors.description ? "category-description-error" : undefined} />
                {fieldErrors.description && <small id="category-description-error" className={styles.fieldError}>{t("descriptionInvalid")}</small>}
                {selected && <div className={styles.slugControl}>
                  <div className={styles.slugSummary}><span>{t("currentUrl")}</span><code>/{selected.slug}</code></div>
                  <label className={styles.slugToggle}><input type="checkbox" checked={editSlug} onChange={(event) => { setEditSlug(event.target.checked); setSlug(selected.slug); }} /><span><strong>{t("editSlugLabel")}</strong><small>{t("editSlugHelp")}</small></span></label>
                  {editSlug && <label>{t("slug")}<div className={styles.slugInput}><span>/</span><input value={slug} onChange={(event) => setSlug(normalizeSlug(event.target.value))} minLength={2} maxLength={100} pattern="[a-z0-9]+(?:-[a-z0-9]+)*" required aria-invalid={Boolean(fieldErrors.slug)} aria-describedby={fieldErrors.slug ? "category-slug-error" : undefined} /></div><small className={styles.warning}>{t("slugWarning")}</small>{fieldErrors.slug && <small id="category-slug-error" className={styles.fieldError}>{t("slugInvalid")}</small>}</label>}
                </div>}
                <div className={styles.formActions}><button type="submit" disabled={busy}>{busy ? t("saving") : selected ? t("save") : t("create")}</button>{selected && <button type="button" className={styles.secondaryButton} onClick={() => choose(null)}>{t("cancel")}</button>}</div>
              </form>
              {selected && <section className={styles.dangerZone} aria-labelledby="delete-category-title">
                <h3 id="delete-category-title">{t("deleteTitle")}</h3>
                <p>{t("deleteDescription")}</p>
                {selected.recipe_count > 0 ? (
                  <p className={styles.deleteBlocked} role="status">{t("deleteBlocked", { count: selected.recipe_count })}</p>
                ) : confirmDelete ? (
                  <div className={styles.deleteConfirmation}>
                    <strong>{t("deleteConfirm", { name: selected.name })}</strong>
                    <div className={styles.dangerActions}>
                      <button type="button" className={styles.dangerButton} onClick={removeSelected} disabled={busy}>{busy ? t("deleting") : t("deleteConfirmAction")}</button>
                      <button type="button" className={styles.dangerCancel} onClick={() => setConfirmDelete(false)} disabled={busy}>{t("keep")}</button>
                    </div>
                  </div>
                ) : (
                  <button type="button" className={styles.dangerOutline} onClick={() => setConfirmDelete(true)}>{t("delete")}</button>
                )}
              </section>}
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
