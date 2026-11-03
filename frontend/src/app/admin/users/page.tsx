"use client";

import Link from "next/link";
import { FormEvent, startTransition, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { getAdminUsers, type AdminUser, type AdminUserPage } from "@/lib/api/admin";
import styles from "./page.module.css";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function AdminUsersPage() {
  const t = useTranslations("adminUsers");
  const [token, setToken] = useState("");
  const [adminName, setAdminName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [query, setQuery] = useState("");
  const [role, setRole] = useState<"" | "Admin" | "Author">("");
  const [page, setPage] = useState(1);
  const [data, setData] = useState<AdminUserPage | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) return;
    startTransition(() => { setLoading(true); setError(""); });
    void getAdminUsers(token, { page, q: query, role: role || undefined })
      .then(setData)
      .catch((cause: unknown) => setError(cause instanceof Error ? cause.message : t("loadError")))
      .finally(() => setLoading(false));
  }, [token, page, query, role, t]);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError("");
    try {
      const response = await fetch(`${apiUrl}/api/v1/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ email, password }) });
      const result = (await response.json()) as { accessToken?: string; user?: { fullName: string; roles: string[] }; detail?: string };
      if (!response.ok) throw new Error(result.detail ?? t("loginError"));
      if (!result.user?.roles.includes("Admin")) throw new Error(t("notAdmin"));
      setToken(result.accessToken ?? ""); setAdminName(result.user.fullName); setPassword("");
    } catch (cause) { setError(cause instanceof Error ? cause.message : t("loginError")); }
    finally { setBusy(false); }
  }

  function signOut() { setToken(""); setAdminName(""); setData(null); }

  if (!token) return <main className={styles.login}><Link href="/admin/categories">← {t("back")}</Link><h1>{t("loginTitle")}</h1><p>{t("loginDescription")}</p><form onSubmit={signIn}><label>{t("email")}<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} required /></label><label>{t("password")}<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} required /></label><button disabled={busy}>{busy ? t("signingIn") : t("signIn")}</button></form>{error && <p role="alert" className={styles.error}>{error}</p>}</main>;

  return <main className={styles.page}>
    <header className={styles.header}><div><Link href="/admin/categories">← {t("back")}</Link><p className={styles.kicker}>{t("eyebrow")}</p><h1>{t("title")}</h1><p>{t("subtitle", { name: adminName })}</p></div><button className={styles.secondary} onClick={signOut}>{t("signOut")}</button></header>
    <section className={styles.toolbar} aria-label={t("filters")}><input value={query} onChange={(event) => { setPage(1); setQuery(event.target.value); }} placeholder={t("searchPlaceholder")} aria-label={t("searchPlaceholder")} /><select value={role} onChange={(event) => { setPage(1); setRole(event.target.value as "" | "Admin" | "Author"); }} aria-label={t("roleFilter")}><option value="">{t("allRoles")}</option><option value="Admin">Admin</option><option value="Author">Author</option></select></section>
    {error && <p role="alert" className={styles.error}>{error}</p>}
    {loading ? <p role="status" className={styles.state}>{t("loading")}</p> : data && data.items.length === 0 ? <p className={styles.state}>{t("empty")}</p> : <div className={styles.tableWrap}><table><thead><tr><th>{t("name")}</th><th>{t("email")}</th><th>{t("userName")}</th><th>{t("role")}</th><th>{t("created")}</th></tr></thead><tbody>{data?.items.map((user: AdminUser) => <tr key={user.id}><td>{user.fullName}</td><td>{user.email}</td><td>{user.userName}</td><td><span className={user.role === "Admin" ? styles.admin : styles.author}>{user.role}</span></td><td>{new Date(user.createdAt).toLocaleDateString()}</td></tr>)}</tbody></table></div>}
    {data && <nav className={styles.pagination} aria-label={t("pagination")}><button disabled={!data.hasPreviousPage || loading} onClick={() => setPage((value) => value - 1)}>←</button><span>{t("page", { page: data.page, total: data.totalPages })}</span><button disabled={!data.hasNextPage || loading} onClick={() => setPage((value) => value + 1)}>→</button></nav>}
  </main>;
}
