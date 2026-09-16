"use client";

import { FormEvent, useState } from "react";

type Mode = "register" | "login";

type AuthUser = {
  fullName: string;
  roles: string[];
};

type AuthResponse = {
  user: AuthUser;
};

type ProblemDetails = {
  detail?: string;
  errors?: Record<string, string[]>;
};

const apiUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function problemMessage(problem: ProblemDetails): string {
  const fieldError = Object.values(problem.errors ?? {}).flat()[0];
  return fieldError ?? problem.detail ?? "Request failed. Please try again.";
}

export function AuthPanel() {
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
        setMessage(problemMessage((await response.json()) as ProblemDetails));
        return;
      }
      const result = (await response.json()) as AuthResponse;
      setUser(result.user);
      setMessage(mode === "register" ? "Account created and signed in." : "Signed in.");
      form.reset();
    } catch {
      setMessage("Cannot reach the API. Check that the backend is running.");
    } finally {
      setPending(false);
    }
  }

  return (
    <section className="auth-section" id="auth" aria-labelledby="auth-title">
      <div className="auth-copy">
        <p className="eyebrow">Your kitchen account</p>
        <h2 id="auth-title">Save a seat at the table.</h2>
        <p>
          Create an Author account, or sign in with email and password. Passwords are
          hashed before storage.
        </p>
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
              {value === "register" ? "Create account" : "Sign in"}
            </button>
          ))}
        </div>
        <form onSubmit={submit}>
          {mode === "register" && (
            <>
              <label>
                Full name
                <input name="fullName" autoComplete="name" maxLength={150} required />
              </label>
              <label>
                User name
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
            Email
            <input name="email" type="email" autoComplete="email" required />
          </label>
          <label>
            Password
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
              Use 8+ characters with uppercase, lowercase, number, and symbol.
            </p>
          )}
          <button className="auth-submit" type="submit" disabled={pending}>
            {pending ? "Working..." : mode === "register" ? "Create account" : "Sign in"}
          </button>
        </form>
        <p className={user ? "auth-message success" : "auth-message"} aria-live="polite">
          {user ? `${message} Welcome, ${user.fullName} (${user.roles.join(", ")}).` : message}
        </p>
      </div>
    </section>
  );
}
