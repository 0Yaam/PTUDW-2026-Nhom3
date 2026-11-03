"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useTranslations } from "next-intl";
import { ApiError, apiRequest } from "@/lib/api/client";
import { clearAuthSession } from "@/lib/auth-session";
import { useAuthStore } from "@/lib/auth-store";
import styles from "./password-security.module.css";

type Mode = "change" | "forgot" | "reset";

export function PasswordSecurity({ mode, token = "" }: { mode: Mode; token?: string }) {
  const t = useTranslations("passwordSecurity");
  const errorT = useTranslations("errors");
  const session = useAuthStore();
  const [pending, setPending] = useState(false);
  const [success, setSuccess] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    const newPassword = String(data.get("newPassword") ?? "");
    const confirmPassword = String(data.get("confirmPassword") ?? "");
    if (mode !== "forgot" && newPassword !== confirmPassword) {
      setMessage(t("passwordMismatch"));
      return;
    }

    const request =
      mode === "forgot"
        ? { path: "/api/v1/auth/forgot-password", body: { email: data.get("email") } }
        : mode === "reset"
          ? { path: "/api/v1/auth/reset-password", body: { token, newPassword } }
          : {
              path: "/api/v1/auth/change-password",
              body: { currentPassword: data.get("currentPassword"), newPassword },
            };

    setPending(true);
    setMessage("");
    try {
      await apiRequest<void>(request.path, {
        method: "POST",
        headers:
          mode === "change" && session
            ? { Authorization: `Bearer ${session.accessToken}` }
            : undefined,
        body: JSON.stringify(request.body),
      });
      if (mode !== "forgot") clearAuthSession();
      setSuccess(true);
      form.reset();
    } catch (error) {
      if (error instanceof ApiError) {
        const type = error.problem.type;
        const fieldError = Object.values(error.problem.errors ?? {}).flat()[0];
        setMessage(
          type && type !== "VALIDATION_ERROR" && errorT.has(type)
            ? errorT(type)
            : fieldError ?? error.problem.detail ?? t("requestFailed"),
        );
      } else {
        setMessage(t("apiUnavailable"));
      }
    } finally {
      setPending(false);
    }
  }

  if (mode === "change" && session === undefined) {
    return <main className={styles.page}><p>{t("checkingSession")}</p></main>;
  }
  if (mode === "change" && session === null) {
    return (
      <main className={styles.page} id="main-content">
        <section className={styles.card}>
          <p className="eyebrow">{t("eyebrow")}</p>
          <h1>{t("signInTitle")}</h1>
          <p>{t("signInDescription")}</p>
          <Link className={styles.primaryLink} href="/#auth">{t("signIn")}</Link>
        </section>
      </main>
    );
  }
  if (mode === "reset" && !token) {
    return (
      <main className={styles.page} id="main-content">
        <section className={styles.card}>
          <p className="eyebrow">{t("eyebrow")}</p>
          <h1>{t("invalidTitle")}</h1>
          <p>{t("invalidDescription")}</p>
          <Link className={styles.primaryLink} href="/forgot-password">{t("requestAnother")}</Link>
        </section>
      </main>
    );
  }

  const title = t(`${mode}Title`);
  const description = t(`${mode}Description`);
  return (
    <main className={styles.page} id="main-content">
      <header className={styles.header}>
        <p className="eyebrow">{t("eyebrow")}</p>
        <h1>{title}</h1>
        <p>{description}</p>
      </header>
      <section className={styles.card} aria-labelledby="password-form-title">
        <h2 id="password-form-title">{title}</h2>
        {success ? (
          <div className={styles.success} role="status">
            <strong>{t(`${mode}SuccessTitle`)}</strong>
            <p>{t(`${mode}SuccessDescription`)}</p>
            <Link className={styles.primaryLink} href={mode === "forgot" ? "/" : "/#auth"}>
              {mode === "forgot" ? t("backHome") : t("signInAgain")}
            </Link>
          </div>
        ) : (
          <form className={styles.form} onSubmit={submit} aria-describedby="password-message">
            {mode === "forgot" && (
              <label>{t("email")}<input name="email" type="email" autoComplete="email" required /></label>
            )}
            {mode === "change" && (
              <label>{t("currentPassword")}<input name="currentPassword" type="password" autoComplete="current-password" required /></label>
            )}
            {mode !== "forgot" && (
              <>
                <label>{t("newPassword")}<input name="newPassword" type="password" autoComplete="new-password" minLength={8} required /></label>
                <p className={styles.hint}>{t("passwordHint")}</p>
                <label>{t("confirmPassword")}<input name="confirmPassword" type="password" autoComplete="new-password" minLength={8} required /></label>
              </>
            )}
            {message && <p id="password-message" className={styles.error} role="alert">{message}</p>}
            <button className={styles.submit} type="submit" disabled={pending}>
              {pending ? t("working") : t(`${mode}Submit`)}
            </button>
          </form>
        )}
      </section>
    </main>
  );
}
