"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import type { Category } from "@/components/category-grid";
import styles from "./page.module.css";

type Problem = { detail?: string; errors?: Record<string, string[]> };
type LoginResponse = {
  accessToken: string;
  user: { fullName: string; roles: string[] };
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function errorText(problem: Problem): string {
  return Object.values(problem.errors ?? {}).flat()[0] ?? problem.detail ?? "Request failed.";
}

export default function ManageCategories() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [token, setToken] = useState("");
  const [adminName, setAdminName] = useState("");
  const [selected, setSelected] = useState<Category | null>(null);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const loadCategories = useCallback(async () => {
    try {
      const response = await fetch(`${apiUrl}/api/v1/categories`, { cache: "no-store" });
      if (!response.ok) throw new Error("Cannot load categories.");
      setCategories((await response.json()) as Category[]);
    } catch {
      setError("Cannot load categories. Check that the API is running.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    void fetch(`${apiUrl}/api/v1/categories`, { cache: "no-store" })
      .then((response) => {
        if (!response.ok) throw new Error("Cannot load categories.");
        return response.json() as Promise<Category[]>;
      })
      .then((items) => { if (active) setCategories(items); })
      .catch(() => { if (active) setError("Cannot load categories. Check that the API is running."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, []);

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
        setError(errorText((await response.json()) as Problem));
        return;
      }
      const result = (await response.json()) as LoginResponse;
      if (!result.user.roles.includes("Admin")) {
        setError("This account does not have Admin access.");
        return;
      }
      setToken(result.accessToken);
      setAdminName(result.user.fullName);
      form.reset();
    } catch {
      setError("Cannot reach the API. Check that the backend is running.");
    } finally {
      setBusy(false);
    }
  }

  function choose(category: Category | null) {
    setSelected(category);
    setName(category?.name ?? "");
    setDescription(category?.description ?? "");
    setError("");
    setMessage("");
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setBusy(true);
    try {
      const response = await fetch(
        selected
          ? `${apiUrl}/api/v1/categories/${selected.id}`
          : `${apiUrl}/api/v1/categories`,
        {
          method: selected ? "PUT" : "POST",
          headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
          body: JSON.stringify({ name, description: description || null }),
        },
      );
      if (!response.ok) {
        if (response.status === 401 || response.status === 403) {
          setToken("");
          setAdminName("");
          setError("Your Admin session is no longer valid. Sign in again.");
        } else {
          setError(errorText((await response.json()) as Problem));
        }
        return;
      }
      const saved = (await response.json()) as Category;
      setMessage(selected ? "Category updated. Its slug stayed the same." : "Category created.");
      setSelected(saved);
      setName(saved.name);
      setDescription(saved.description ?? "");
      await loadCategories();
    } catch {
      setError("Cannot reach the API. Check that the backend is running.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className={styles.shell}>
      <header className={styles.header}>
        <Link className={styles.brand} href="/">SK <span>Small Kitchen</span></Link>
        <Link href="/">Back to home &rarr;</Link>
      </header>
      <div className={styles.intro}>
        <p className={styles.kicker}>Kitchen administration / Categories</p>
        <h1>Shape the menu.</h1>
        <p>Create a category or update its name and description. An existing URL slug stays in place when you rename it.</p>
      </div>

      {!token ? (
        <section className={styles.login} aria-labelledby="admin-login">
          <p className={styles.kicker}>Admin access</p>
          <h2 id="admin-login">Sign in to manage categories</h2>
          <p className={styles.help}>
            New here? <Link href="/#auth">Create an account on the homepage</Link> first.
            New accounts have the Author role; an existing Admin must grant Admin
            access before this page can manage categories.
          </p>
          <form onSubmit={signIn} className={styles.form}>
            <label>Email<input name="email" type="email" autoComplete="email" required /></label>
            <label>Password<input name="password" type="password" autoComplete="current-password" required /></label>
            <button type="submit" disabled={busy}>{busy ? "Signing in..." : "Sign in"}</button>
          </form>
        </section>
      ) : (
        <div className={styles.workspace}>
          <section aria-labelledby="list-title" className={styles.listPanel}>
            <div className={styles.panelHead}>
              <div><p className={styles.kicker}>Welcome, {adminName}</p><h2 id="list-title">Categories</h2></div>
              <button type="button" onClick={() => choose(null)}>+ New</button>
            </div>
            {loading ? <p>Loading categories...</p> : categories.length === 0 ? <p>No categories yet. Create the first one.</p> : (
              <ul className={styles.list}>
                {categories.map((category) => (
                  <li key={category.id}>
                    <button type="button" className={selected?.id === category.id ? styles.active : ""} onClick={() => choose(category)}>
                      <strong>{category.name}</strong><small>/{category.slug}</small>
                    </button>
                  </li>
                ))}
              </ul>
            )}
            <button type="button" className={styles.signOut} onClick={() => { setToken(""); setAdminName(""); choose(null); }}>Sign out</button>
          </section>
          <section className={styles.editor} aria-labelledby="editor-title">
            <p className={styles.kicker}>{selected ? "Edit category" : "New category"}</p>
            <h2 id="editor-title">{selected ? selected.name : "Add something delicious"}</h2>
            <form onSubmit={save} className={styles.form}>
              <label>Name<input value={name} onChange={(event) => setName(event.target.value)} minLength={2} maxLength={50} required /></label>
              <label>Description<textarea value={description} onChange={(event) => setDescription(event.target.value)} rows={5} /></label>
              {selected && <p className={styles.slugNote}>Stable URL: <code>/{selected.slug}</code></p>}
              <button type="submit" disabled={busy}>{busy ? "Saving..." : selected ? "Save changes" : "Create category"}</button>
            </form>
          </section>
        </div>
      )}
      <p role="alert" className={styles.error}>{error}</p>
      <p role="status" className={styles.success}>{message}</p>
    </main>
  );
}
