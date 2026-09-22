"use client";

import Link from "next/link";
import { FormEvent, useState } from "react";
import { useTranslations } from "next-intl";
import { saveAuthSession } from "@/lib/auth-session";

type Mode = "register" | "login";

type AuthUser = {
  fullName: string;
  roles: string[];
};

type AuthResponse = {
  accessToken: string;
  expiresAt: string;
  user: AuthUser;
};

type ProblemDetails = {
  type?: string;
  detail?: string;
  errors?: Record<string, string[]>;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export function AuthPanel() {
  const t = useTranslations("auth");
  const errorT = useTranslations("errors");
  const [mode, setMode] = useState<Mode>("register");
  const [message, setMessage] = useState("");
  const [user, setUser] = useState<AuthUser | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setPending(true);
    const form = event.currentTarget;
    const data = new FormData(form);
    const payload =
      mode === "register"
        ? {
            fullName: data.get("fullName"),
            email: data.get("email"),
            userName: data.get("userName"),
            password: data.get("password"),
          }
        : { email: data.get("email"), password: data.get("password") };

    try {
      const response = await fetch(`${apiUrl}/api/v1/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        const problem = (await response.json()) as ProblemDetails;
        const knownType = problem.type && errorT.has(problem.type) ? problem.type : null;
        const fieldError = Object.values(problem.errors ?? {}).flat()[0];
        setMessage(knownType ? errorT(knownType) : fieldError ?? problem.detail ?? t("requestFailed"));
        return;
      }
      const result = (await response.json()) as AuthResponse;
      saveAuthSession(result);
      setUser(result.user);
      setMessage(mode === "register" ? t("registered") : t("signedIn"));
      form.reset();
    } catch {
      setMessage(t("apiUnavailable"));
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="auth-section" id="auth" aria-labelledby="auth-title">
      <div className="auth-copy">
        <p className="eyebrow">{t("eyebrow")}</p>
        <h2 id="auth-title">{t("title")}</h2>
        <p>{t("description")}</p>
      </div>
      <div className="auth-card">
        <div className="auth-tabs" aria-label="Account action">
          {(["register", "login"] as const).map((value) => (
            <button
              type="button"
              key={value}
              aria-pressed={mode === value}
              onClick={() => {
                setMode(value);
                setMessage("");
                setUser(null);
              }}
            >
              {value === "register" ? t("register") : t("login")}
            </button>
          ))}
        </div>
        <form onSubmit={submit}>
          {mode === "register" && (
            <>
              <label>
                {t("fullName")}
                <input name="fullName" autoComplete="name" maxLength={150} required />
              </label>
              <label>
                {t("userName")}
                <input
                  name="userName"
                  autoComplete="username"
                  minLength={3}
                  maxLength={50}
                  pattern="[A-Za-z0-9_]+"
                  required
                />
              </label>
            </>
          )}
          <label>
            {t("email")}
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            {t("password")}
            <input
              name="password"
              type="password"
              autoComplete={mode === "register" ? "new-password" : "current-password"}
              minLength={mode === "register" ? 8 : 1}
              required
            />
          </label>
          {mode === "register" && (
            <p className="field-note">
              {t("passwordHint")}
            </p>
          )}
          <button className="auth-submit" type="submit" disabled={pending}>
            {pending ? t("working") : mode === "register" ? t("register") : t("login")}
          </button>
        </form>
        <p className={user ? "auth-message success" : "auth-message"} aria-live="polite">
          {user ? t("welcome", { message, name: user.fullName, roles: user.roles.join(", ") }) : message}
        </p>
        {user && <Link className="primary-action" href="/recipes/new">{t("createRecipe")}</Link>}
      </div>
    </section>
  );
}
