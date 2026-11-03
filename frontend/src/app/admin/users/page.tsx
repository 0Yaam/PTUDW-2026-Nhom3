"use client";

import { FormEvent, Suspense, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { LocaleSwitcher } from "@/components/locale-switcher";
import {
  getAdminUsers,
  type AdminLoginResponse,
  type AdminUser,
  type PagedAdminUsers,
} from "@/lib/api/admin";
import { ApiError } from "@/lib/api/client";
import {
  clearAuthSession,
  loadActiveAuthSession,
  saveAuthSession,
  type AuthSession,
} from "@/lib/auth-session";
import { useAuthStore } from "@/lib/auth-store";
import styles from "./page.module.css";

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type IconName = "spark" | "grid" | "list" | "users" | "chat" | "chart" | "settings" | "external" | "search";

const iconPaths: Record<IconName, string> = {
  spark: "M12 2 14.2 9.8 22 12l-7.8 2.2L12 22l-2.2-7.8L2 12l7.8-2.2L12 2Z",
  grid: "M3 3h7v7H3zM14 3h7v7h-7zM3 14h7v7H3zM14 14h7v7h-7z",
  list: "M4 5h16M4 12h16M4 19h16",
  users: "M16 20v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2h14ZM9 10a3 3 0 1 0 0-6 3 3 0 0 0 0 6Zm13 10v-2a4 4 0 0 0-3-3.87M16 4.13a3 3 0 0 1 0 5.74",
  chat: "M4 4h16v12H8l-4 4V4Zm4 4h8m-8 4h6",
  chart: "M4 20V4m0 16h16M8 16l4-5 3 2 5-7",
  settings: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Zm0-6v3m0 14v3M4.9 4.9 7 7m10 10 2.1 2.1M2 12h3m14 0h3M4.9 19.1 7 17M17 7l2.1-2.1",
  external: "M13 4h7v7m0-7-9 9M20 14v6H4V4h6",
  search: "M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14Zm5-2 5 5",
};

function AdminIcon({ name }: { name: IconName }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d={iconPaths[name]} />
    </svg>
  );
}

function UsersContent() {
  const t = useTranslations("admin");
  const errors = useTranslations("errors");
  const locale = useLocale();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const storeSession = useAuthStore();
  const [token, setToken] = useState("");
  const [adminName, setAdminName] = useState("");
  const [sessionChecked, setSessionChecked] = useState(false);
  const [isForbidden, setIsForbidden] = useState(false);

  // Filter & pagination state
  const qParam = searchParams.get("q") ?? "";
  const roleParam = searchParams.get("role") ?? "";
  const pageParam = Math.max(1, parseInt(searchParams.get("page") ?? "1", 10) || 1);

  const [search, setSearch] = useState(qParam);
  const [roleFilter, setRoleFilter] = useState(roleParam);
  const [page, setPage] = useState(pageParam);

  const [data, setData] = useState<PagedAdminUsers | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  // Synchronize URL query params
  const updateQuery = useCallback(
    (newQ: string, newRole: string, newPage: number) => {
      const params = new URLSearchParams();
      if (newQ.trim()) params.set("q", newQ.trim());
      if (newRole) params.set("role", newRole);
      if (newPage > 1) params.set("page", String(newPage));
      const str = params.toString();
      router.replace(str ? `${pathname}?${str}` : pathname, { scroll: false });
    },
    [pathname, router],
  );

  // Check auth session
  useEffect(() => {
    let active = true;
    void loadActiveAuthSession().then((activeSession) => {
      if (!active) return;
      if (activeSession && activeSession.user.roles.includes("Admin")) {
        setToken(activeSession.accessToken);
        setAdminName(activeSession.user.fullName);
        setIsForbidden(false);
      } else if (activeSession && !activeSession.user.roles.includes("Admin")) {
        setIsForbidden(true);
      }
      setSessionChecked(true);
    });
    return () => {
      active = false;
    };
  }, [storeSession]);

  // Manual reload for refresh button / retry
  async function reloadUsers(authToken: string, qVal: string, roleVal: string, pageVal: number) {
    setLoading(true);
    setError("");
    try {
      const result = await getAdminUsers(
        {
          page: pageVal,
          pageSize: 10,
          q: qVal.trim() || undefined,
          role: roleVal || undefined,
        },
        authToken,
      );
      setData(result);
    } catch (err: unknown) {
      if (err instanceof ApiError) {
        if (err.status === 403) {
          setIsForbidden(true);
          return;
        }
        if (err.status === 401) {
          setToken("");
          setError(t("sessionExpired"));
          return;
        }
      }
      setError(t("usersError"));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;
    if (token) {
      void getAdminUsers(
        {
          page: pageParam,
          pageSize: 10,
          q: qParam.trim() || undefined,
          role: roleParam || undefined,
        },
        token,
      )
        .then((result) => {
          if (active) {
            setData(result);
            setLoading(false);
          }
        })
        .catch((err: unknown) => {
          if (active) {
            if (err instanceof ApiError) {
              if (err.status === 403) {
                setIsForbidden(true);
                return;
              }
              if (err.status === 401) {
                setToken("");
                setError(t("sessionExpired"));
                return;
              }
            }
            setError(t("usersError"));
            setLoading(false);
          }
        });
    }
    return () => {
      active = false;
    };
  }, [token, qParam, roleParam, pageParam, t]);

  // Direct login for guest landing on /admin/users
  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setBusy(true);
    const form = event.currentTarget;
    const body = new FormData(form);
    try {
      const response = await fetch(`${apiUrl}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: body.get("email"), password: body.get("password") }),
      });
      if (!response.ok) {
        setError(errors("UNAUTHORIZED"));
        return;
      }
      const result = (await response.json()) as AdminLoginResponse & { refreshToken?: string; expiresAt?: string };
      if (!result.user.roles.includes("Admin")) {
        setError(t("notAdmin"));
        setIsForbidden(true);
        return;
      }
      if (result.refreshToken && result.expiresAt) {
        saveAuthSession(result as AuthSession);
      }
      setToken(result.accessToken);
      setAdminName(result.user.fullName);
      setIsForbidden(false);
      form.reset();
    } catch {
      setError(t("apiUnavailable"));
    } finally {
      setBusy(false);
    }
  }

  function handleSignOut() {
    clearAuthSession();
    setToken("");
    setAdminName("");
    setData(null);
    setIsForbidden(false);
  }

  function onSearchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setPage(1);
    updateQuery(search, roleFilter, 1);
  }

  function onRoleChange(nextRole: string) {
    setRoleFilter(nextRole);
    setPage(1);
    updateQuery(search, nextRole, 1);
  }

  function onPageChange(nextPage: number) {
    setPage(nextPage);
    updateQuery(search, roleFilter, nextPage);
  }

  function formatDate(iso: string): string {
    try {
      const d = new Date(iso);
      return d.toLocaleDateString(locale === "vi" ? "vi-VN" : "en-US", {
        year: "numeric",
        month: "short",
        day: "numeric",
      });
    } catch {
      return iso;
    }
  }

  // Forbidden state for signed-in non-admin
  if (isForbidden) {
    return (
      <main id="main-content" className={styles.dashboard}>
        <div className={styles.forbiddenShell} role="alert">
          <div className={`${styles.stateIcon} ${styles.forbiddenIcon}`} aria-hidden="true">
            ✕
          </div>
          <h2>{t("usersForbiddenTitle")}</h2>
          <p>{t("usersForbiddenDescription")}</p>
          <button type="button" onClick={handleSignOut}>
            {t("usersForbiddenAction")}
          </button>
        </div>
      </main>
    );
  }

  // Not signed in / no token -> Admin login shell
  if (!token && sessionChecked) {
    return (
      <main id="main-content" className={styles.loginShell}>
        <section className={styles.loginBrand}>
          <Link className={styles.brand} href="/">
            <span><AdminIcon name="spark" /></span>
            {t("brand")}
          </Link>
          <blockquote>{t("loginQuote")}</blockquote>
        </section>
        <section className={styles.loginCard} aria-labelledby="admin-login">
          <div className={styles.loginToolbar}>
            <Link href="/">← {t("visitSite")}</Link>
            <LocaleSwitcher compact />
          </div>
          <p className={styles.kicker}>{t("access")}</p>
          <h1 id="admin-login">{t("loginTitle")}</h1>
          <p className={styles.muted}>{t("loginDescription")}</p>
          <form onSubmit={signIn} className={styles.form}>
            <label>
              {t("email")}
              <input name="email" type="email" autoComplete="email" required />
            </label>
            <label>
              {t("password")}
              <input name="password" type="password" autoComplete="current-password" required />
            </label>
            <button type="submit" disabled={busy}>
              {busy ? t("signingIn") : t("signIn")}
            </button>
          </form>
          <p className={styles.help}>
            {t("newHere")} <Link href="/#auth">{t("registerLink")}</Link>. {t("roleHint")}
          </p>
          {error && <p role="alert" className={styles.error}>{error}</p>}
        </section>
      </main>
    );
  }

  return (
    <main id="main-content" className={styles.dashboard}>
      <aside className={styles.sidebar}>
        <Link className={styles.brand} href="/">
          <span><AdminIcon name="spark" /></span>
          {t("brand")}
        </Link>

        <p className={styles.navLabel}>{t("workspace")}</p>
        <nav aria-label={t("workspace")}>
          <Link className={styles.navItem} href="/admin/categories#overview">
            <AdminIcon name="grid" />
            {t("navOverview")}
          </Link>
          <Link className={styles.navItem} href="/admin/categories">
            <AdminIcon name="list" />
            {t("categories")}
          </Link>
        </nav>

        <p className={styles.navLabel}>{t("management")}</p>
        <nav aria-label={t("management")}>
          <Link className={`${styles.navItem} ${styles.navItemActive}`} href="/admin/users">
            <AdminIcon name="users" />
            {t("navUsers")}
          </Link>
          <div className={styles.navItemDisabled} aria-disabled="true">
            <AdminIcon name="chat" />
            {t("navComments")}
            <small>{t("comingSoon")}</small>
          </div>
          <div className={styles.navItemDisabled} aria-disabled="true">
            <AdminIcon name="chart" />
            {t("navAnalytics")}
            <small>{t("comingSoon")}</small>
          </div>
        </nav>

        <p className={styles.navLabel}>{t("system")}</p>
        <nav aria-label={t("system")}>
          <div className={styles.navItemDisabled} aria-disabled="true">
            <AdminIcon name="settings" />
            {t("navSettings")}
            <small>{t("comingSoon")}</small>
          </div>
          <Link className={styles.navItem} href="/">
            <AdminIcon name="external" />
            {t("visitSite")}
          </Link>
        </nav>

        <div className={styles.sidebarAccount}>
          <span className={styles.avatar} aria-hidden="true">
            {adminName ? adminName.slice(0, 1).toUpperCase() : "A"}
          </span>
          <div>
            <p>{adminName || t("brand")}</p>
            <p>Admin</p>
          </div>
          <button type="button" onClick={handleSignOut}>
            {t("signOut")}
          </button>
        </div>
      </aside>

      <div className={styles.page}>
        <div className={styles.mobileBrand}>
          <Link className={styles.brand} href="/">
            <span><AdminIcon name="spark" /></span>
            {t("brand")}
          </Link>
          <LocaleSwitcher compact />
        </div>

        <div className={styles.pageHead}>
          <div>
            <p className={styles.kicker}>{t("usersKicker")}</p>
            <h1>{t("usersTitle")}</h1>
            <p>{t("usersSubtitle")}</p>
          </div>
          <button
            type="button"
            className={styles.refreshButton}
            onClick={() => token && void reloadUsers(token, search, roleFilter, page)}
            disabled={loading}
          >
            <AdminIcon name="spark" />
            {t("refreshUsers")}
          </button>
        </div>

        <div className={styles.panel}>
          <div className={styles.panelHead}>
            <form className={styles.filters} onSubmit={onSearchSubmit}>
              <div className={styles.searchBox}>
                <AdminIcon name="search" />
                <input
                  type="search"
                  value={search}
                  placeholder={t("usersSearchPlaceholder")}
                  onChange={(e) => setSearch(e.target.value)}
                />
              </div>

              <select
                className={styles.roleSelect}
                value={roleFilter}
                aria-label={t("filterRole")}
                onChange={(e) => onRoleChange(e.target.value)}
              >
                <option value="">{t("allRoles")}</option>
                <option value="Admin">{t("roleAdmin")}</option>
                <option value="Author">{t("roleAuthor")}</option>
              </select>
            </form>

            <span className={styles.userCountBadge}>
              {data ? t("userCount", { count: data.totalCount }) : ""}
            </span>
          </div>

          {error ? (
            <div className={styles.errorStateBox} role="alert">
              <div className={`${styles.stateIcon} ${styles.errorIcon}`} aria-hidden="true">!</div>
              <h2>{t("usersError")}</h2>
              <button
                type="button"
                onClick={() => token && void reloadUsers(token, search, roleFilter, page)}
              >
                {t("refreshUsers")}
              </button>
            </div>
          ) : loading && !data ? (
            <div className={styles.emptyStateBox} aria-busy="true">
              <p>{t("usersLoading")}</p>
            </div>
          ) : data && data.items.length === 0 ? (
            <div className={styles.emptyStateBox}>
              <div className={`${styles.stateIcon} ${styles.emptyIcon}`} aria-hidden="true">✳</div>
              <h2>{t("usersEmpty")}</h2>
              <p>{t("usersEmptyHint")}</p>
            </div>
          ) : data ? (
            <>
              <div className={styles.tableScroll}>
                <table className={styles.table}>
                  <thead>
                    <tr>
                      <th scope="col">{t("colFullName")}</th>
                      <th scope="col">{t("colUserName")}</th>
                      <th scope="col">{t("colEmail")}</th>
                      <th scope="col">{t("colRole")}</th>
                      <th scope="col">{t("colJoined")}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.items.map((user: AdminUser) => (
                      <tr key={user.id}>
                        <td>
                          <div className={styles.userCell}>
                            <span className={styles.userAvatar} aria-hidden="true">
                              {user.fullName.slice(0, 1).toUpperCase()}
                            </span>
                            <div className={styles.userNameBlock}>
                              <span className={styles.userFullName}>{user.fullName}</span>
                            </div>
                          </div>
                        </td>
                        <td>
                          <span className={styles.userHandle}>@{user.userName}</span>
                        </td>
                        <td>{user.email}</td>
                        <td>
                          <span
                            className={`${styles.roleBadge} ${
                              user.role === "Admin" ? styles.roleAdmin : styles.roleAuthor
                            }`}
                          >
                            {user.role === "Admin" ? t("roleAdmin") : t("roleAuthor")}
                          </span>
                        </td>
                        <td>
                          <span className={styles.joinedDate}>{formatDate(user.createdAt)}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <nav className={styles.pagination} aria-label={t("userPagination")}>
                <button
                  type="button"
                  onClick={() => onPageChange(data.page - 1)}
                  disabled={!data.hasPreviousPage || loading}
                >
                  {t("previous")}
                </button>
                <span className={styles.paginationInfo}>
                  {t("pageOf", { page: data.page, total: data.totalPages || 1 })}
                </span>
                <button
                  type="button"
                  onClick={() => onPageChange(data.page + 1)}
                  disabled={!data.hasNextPage || loading}
                >
                  {t("next")}
                </button>
              </nav>
            </>
          ) : null}
        </div>
      </div>
    </main>
  );
}

export default function AdminUsersPage() {
  return (
    <Suspense fallback={<div className={styles.dashboard} />}>
      <UsersContent />
    </Suspense>
  );
}
