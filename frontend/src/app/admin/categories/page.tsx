"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import type { Category } from "@/components/category-grid";
import { LocaleSwitcher } from "@/components/locale-switcher";
import styles from "./page.module.css";

type Problem = { type?: string; detail?: string; errors?: Record<string, string[]> };
type LoginResponse = { accessToken: string; user: { fullName: string; roles: string[] } };

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

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
    setError("");
    setMessage("");
  }

  function signOut() {
    setToken("");
    setAdminName("");
    choose(null);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
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
          setError(t("sessionExpired"));
        } else {
          setError(problemText((await response.json()) as Problem));
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
      await loadCategories();
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
          <Link className={styles.brand} href="/"><span aria-hidden="true">✳</span>{t("brand")}</Link>
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
        <Link className={styles.brand} href="/"><span aria-hidden="true">✳</span>{t("brand")}</Link>
        <p className={styles.navLabel}>{t("workspace")}</p>
        <nav aria-label={t("workspace")}>
          <div className={styles.navItemDisabled} aria-disabled="true"><span aria-hidden="true">⌂</span>{t("navOverview")}<small>{t("comingSoon")}</small></div>
        </nav>
        <p className={styles.navLabel}>{t("content")}</p>
        <nav aria-label={t("content")}>
          <a className={styles.navItemActive} href="#category-list"><span aria-hidden="true">▦</span>{t("categories")}</a>
          <div className={styles.navItemDisabled} aria-disabled="true"><span aria-hidden="true">⌑</span>{t("navRecipes")}<small>{t("comingSoon")}</small></div>
          <div className={styles.navItemDisabled} aria-disabled="true"><span aria-hidden="true">▤</span>{t("navPosts")}<small>{t("comingSoon")}</small></div>
          <div className={styles.navItemDisabled} aria-disabled="true"><span aria-hidden="true">▧</span>{t("navMedia")}<small>{t("comingSoon")}</small></div>
        </nav>
        <p className={styles.navLabel}>{t("management")}</p>
        <nav aria-label={t("management")}>
          <div className={styles.navItemDisabled} aria-disabled="true"><span aria-hidden="true">♙</span>{t("navUsers")}<small>{t("comingSoon")}</small></div>
          <div className={styles.navItemDisabled} aria-disabled="true"><span aria-hidden="true">◫</span>{t("navComments")}<small>{t("comingSoon")}</small></div>
          <div className={styles.navItemDisabled} aria-disabled="true"><span aria-hidden="true">⌁</span>{t("navAnalytics")}<small>{t("comingSoon")}</small></div>
        </nav>
        <p className={styles.navLabel}>{t("system")}</p>
        <nav aria-label={t("system")}>
          <div className={styles.navItemDisabled} aria-disabled="true"><span aria-hidden="true">⚙</span>{t("navSettings")}<small>{t("comingSoon")}</small></div>
          <Link className={styles.navItem} href="/"><span aria-hidden="true">↗</span>{t("visitSite")}</Link>
        </nav>
        <div className={styles.sidebarAccount}>
          <span className={styles.avatar} aria-hidden="true">{adminName.slice(0, 1).toUpperCase()}</span>
          <div><strong>{adminName}</strong><small>{t("signedInAs")}</small></div>
          <button type="button" onClick={signOut}>{t("signOut")}</button>
        </div>
      </aside>

      <div className={styles.content}>
        <header className={styles.topbar}>
          <button className={styles.mobileBrand} type="button" aria-label={t("categories")}>✳</button>
          <span>{t("breadcrumb")}</span>
          <div className={styles.activeModule}><i aria-hidden="true" />{t("activeModule")}</div>
          <LocaleSwitcher compact />
        </header>
        <div className={styles.page}>
          <div className={styles.pageHead}>
            <div><p className={styles.kicker}>{t("breadcrumb")}</p><h1>{t("title")}</h1><p>{t("subtitle")}</p></div>
            <button className={styles.primaryButton} type="button" onClick={() => choose(null)}>+ {t("new")}</button>
          </div>

          <section className={styles.stats} aria-label={t("title")}>
            <article><span className={styles.statIcon} aria-hidden="true">▦</span><div><p>{t("totalCategories")}</p><strong>{categories.length}</strong></div></article>
            <article><span className={styles.statIcon} aria-hidden="true">☷</span><div><p>{t("totalRecipes")}</p><strong>{recipeTotal}</strong></div></article>
            <article><span className={styles.statIcon} aria-hidden="true">↗</span><div><p>{t("stableSlugs")}</p><strong>{categories.length}</strong></div></article>
          </section>

          <div className={styles.workspace}>
            <section id="category-list" className={styles.tablePanel} aria-labelledby="list-title">
              <div className={styles.panelHead}>
                <div><h2 id="list-title">{t("listTitle")}</h2><p>{t("listHint")}</p></div>
                <label className={styles.searchBox}><span aria-hidden="true">⌕</span><span className={styles.srOnly}>{t("search")}</span><input value={search} onChange={(event) => setSearch(event.target.value)} placeholder={t("searchPlaceholder")} /></label>
              </div>
              {loading ? <p className={styles.state}>{t("loading")}</p> : categories.length === 0 ? <p className={styles.state}>{t("empty")}</p> : (
                filteredCategories.length === 0 ? <p className={styles.state}>{t("noResults")}</p> : <div className={styles.tableScroll}><table>
                  <thead><tr><th>{t("tableName")}</th><th>{t("tableSlug")}</th><th>{t("tableRecipes")}</th><th><span className={styles.srOnly}>{t("tableAction")}</span></th></tr></thead>
                  <tbody>{filteredCategories.map((category) => (
                    <tr key={category.id} className={selected?.id === category.id ? styles.selectedRow : ""}>
                      <td><strong>{category.name}</strong><small>{category.description ?? "—"}</small></td>
                      <td><code>/{category.slug}</code></td><td>{category.recipe_count}</td>
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
                <label>{t("name")}<input value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={50} required /></label>
                <label>{t("description")}<textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder={t("descriptionPlaceholder")} rows={5} /></label>
                {selected && <div className={styles.slugControl}>
                  <div className={styles.slugSummary}><span>{t("currentUrl")}</span><code>/{selected.slug}</code></div>
                  <label className={styles.slugToggle}><input type="checkbox" checked={editSlug} onChange={(event) => { setEditSlug(event.target.checked); setSlug(selected.slug); }} /><span><strong>{t("editSlugLabel")}</strong><small>{t("editSlugHelp")}</small></span></label>
                  {editSlug && <label>{t("slug")}<div className={styles.slugInput}><span>/</span><input value={slug} onChange={(event) => setSlug(normalizeSlug(event.target.value))} minLength={2} maxLength={100} pattern="[a-z0-9]+(?:-[a-z0-9]+)*" required /></div><small className={styles.warning}>{t("slugWarning")}</small></label>}
                </div>}
                <div className={styles.formActions}><button type="submit" disabled={busy}>{busy ? t("saving") : selected ? t("save") : t("create")}</button>{selected && <button type="button" className={styles.secondaryButton} onClick={() => choose(null)}>{t("cancel")}</button>}</div>
              </form>
              {error && <p role="alert" className={styles.error}>{error}</p>}
              {message && <p role="status" className={styles.success}>{message}</p>}
            </section>
          </div>
        </div>
      </div>
    </main>
  );
}
