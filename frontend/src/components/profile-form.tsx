"use client";

import Link from "next/link";
import { FormEvent, useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  ProfileApiError,
  type Profile,
  getProfile,
  updateProfile,
} from "@/lib/api/profile";
import {
  AUTH_SESSION_CHANGED,
  clearAuthSession,
  loadActiveAuthSession,
  type AuthSession,
} from "@/lib/auth-session";
import styles from "./profile-form.module.css";

type FieldErrors = Record<string, string>;

export function ProfileForm() {
  const t = useTranslations("profile");
  const errorT = useTranslations("errors");
  const [session, setSession] = useState<AuthSession | null | undefined>(undefined);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [loadFailed, setLoadFailed] = useState(false);
  const [reloadKey, setReloadKey] = useState(0);
  const [pending, setPending] = useState(false);
  const [saved, setSaved] = useState(false);
  const [formError, setFormError] = useState("");
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({});
  const [fullName, setFullName] = useState("");
  const [userName, setUserName] = useState("");
  const [avatarUrl, setAvatarUrl] = useState("");

  const fillForm = useCallback((loaded: Profile) => {
    setProfile(loaded);
    setFullName(loaded.fullName);
    setUserName(loaded.userName);
    setAvatarUrl(loaded.avatarUrl ?? "");
  }, []);

  useEffect(() => {
    const updateSession = () => void loadActiveAuthSession().then(setSession);
    updateSession();
    window.addEventListener(AUTH_SESSION_CHANGED, updateSession);
    return () => window.removeEventListener(AUTH_SESSION_CHANGED, updateSession);
  }, []);

  useEffect(() => {
    if (!session) return;

    let active = true;
    async function loadProfile(accessToken: string) {
      try {
        const loaded = await getProfile(accessToken);
        if (active) fillForm(loaded);
      } catch (error) {
        if (!active) return;
        if (error instanceof ProfileApiError && error.status === 401) {
          clearAuthSession();
          return;
        }
        setLoadFailed(true);
      }
    }
    void loadProfile(session.accessToken);
    return () => { active = false; };
  }, [session, reloadKey, fillForm]);

  function validate(): FieldErrors {
    const errors: FieldErrors = {};
    const name = fullName.trim();
    const handle = userName.trim();
    const avatar = avatarUrl.trim();
    if (name.length < 1 || name.length > 150) errors.fullName = t("validation.fullName");
    if (!/^[A-Za-z0-9_]{3,50}$/.test(handle)) errors.userName = t("validation.userName");
    if (avatar && !/^https?:\/\//.test(avatar)) errors.avatarUrl = t("validation.avatarUrl");
    if (avatar.length > 500) errors.avatarUrl = t("validation.avatarUrl");
    return errors;
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!session) return;

    const errors = validate();
    setFieldErrors(errors);
    setFormError("");
    setSaved(false);
    if (Object.keys(errors).length > 0) return;

    setPending(true);
    try {
      fillForm(
        await updateProfile(
          {
            fullName: fullName.trim(),
            userName: userName.trim(),
            avatarUrl: avatarUrl.trim() || null,
          },
          session.accessToken,
        ),
      );
      setSaved(true);
    } catch (error) {
      if (!(error instanceof ProfileApiError)) {
        setFormError(t("apiUnavailable"));
        return;
      }
      if (error.status === 401) {
        clearAuthSession();
        setFormError(t("sessionExpired"));
        return;
      }
      if (error.status === 422 && error.problem.errors) {
        setFieldErrors(
          Object.fromEntries(
            Object.entries(error.problem.errors).map(([field, messages]) => [field, messages[0]]),
          ),
        );
        setFormError(t("validationSummary"));
        return;
      }
      const type = error.problem.type;
      const message = type && errorT.has(type) ? errorT(type) : error.problem.detail ?? t("requestFailed");
      if (error.status === 409) setFieldErrors({ userName: message });
      setFormError(message);
    } finally {
      setPending(false);
    }
  }

  const dirty =
    profile !== null &&
    (fullName !== profile.fullName ||
      userName !== profile.userName ||
      avatarUrl !== (profile.avatarUrl ?? ""));

  return (
    <main id="main-content" className={styles.page}>
      <div className={styles.shell}>
        <header className={styles.pageHeader}>
          <Link className={styles.backLink} href="/">← {t("back")}</Link>
          <p className={styles.eyebrow}>{t("eyebrow")}</p>
          <h1>{t("title")}</h1>
          <p className={styles.intro}>{t("description")}</p>
        </header>

        {session === undefined ? (
          <section className={styles.centerState}><p>{t("checkingSession")}</p></section>
        ) : !session ? (
          <section className={styles.centerState}>
            <span aria-hidden="true">✳</span>
            <h2>{t("signInTitle")}</h2>
            <p>{t("signInDescription")}</p>
            <Link className={styles.primaryLink} href="/#auth">{t("signIn")}</Link>
          </section>
        ) : loadFailed ? (
          <section className={styles.centerState}>
            <span aria-hidden="true">⚠</span>
            <h2>{t("loadErrorTitle")}</h2>
            <p>{t("loadErrorDescription")}</p>
            <button
              className={styles.primaryLink}
              type="button"
              onClick={() => { setLoadFailed(false); setReloadKey((key) => key + 1); }}
            >
              {t("retry")}
            </button>
          </section>
        ) : !profile ? (
          <section className={styles.centerState}><p>{t("loading")}</p></section>
        ) : (
          <>
            {saved && (
              <section className={styles.banner} aria-live="polite">
                <span aria-hidden="true">✓</span>
                <div><strong>{t("savedTitle")}</strong><p>{t("savedDescription")}</p></div>
              </section>
            )}

            <section className={styles.card}>
              <div className={styles.identity}>
                {profile.avatarUrl ? (
                  // An avatar may live on any host, and next/image needs each one listed
                  // in next.config, so a plain img is the only thing that works here.
                  // eslint-disable-next-line @next/next/no-img-element
                  <img className={styles.avatar} src={profile.avatarUrl} alt="" width={58} height={58} />
                ) : (
                  <span className={`${styles.avatar} ${styles.avatarFallback}`} aria-hidden="true">
                    {profile.fullName.trim().charAt(0).toUpperCase() || "?"}
                  </span>
                )}
                <div>
                  <h2>{profile.fullName}</h2>
                  <p className={styles.identityMeta}>
                    @{profile.userName}
                    <span className={styles.roles}>
                      {profile.roles.map((role) => <span key={role}>{role}</span>)}
                    </span>
                  </p>
                </div>
              </div>

              <form className={styles.form} onSubmit={submit} noValidate>
                <label>
                  {t("fullName")}
                  <input
                    name="fullName"
                    value={fullName}
                    onChange={(event) => setFullName(event.target.value)}
                    maxLength={150}
                    aria-invalid={Boolean(fieldErrors.fullName)}
                    aria-describedby={fieldErrors.fullName ? "full-name-error" : undefined}
                  />
                </label>
                {fieldErrors.fullName && <p id="full-name-error" className={styles.fieldError}>{fieldErrors.fullName}</p>}

                <label>
                  {t("userName")}
                  <input
                    name="userName"
                    value={userName}
                    onChange={(event) => setUserName(event.target.value)}
                    minLength={3}
                    maxLength={50}
                    aria-invalid={Boolean(fieldErrors.userName)}
                    aria-describedby={fieldErrors.userName ? "user-name-error" : "user-name-hint"}
                  />
                </label>
                {fieldErrors.userName ? (
                  <p id="user-name-error" className={styles.fieldError}>{fieldErrors.userName}</p>
                ) : (
                  <p id="user-name-hint" className={styles.hint}>{t("userNameHint")}</p>
                )}

                <label>
                  {t("avatarUrl")}
                  <input
                    name="avatarUrl"
                    type="url"
                    value={avatarUrl}
                    onChange={(event) => setAvatarUrl(event.target.value)}
                    maxLength={500}
                    placeholder="https://"
                    aria-invalid={Boolean(fieldErrors.avatarUrl)}
                    aria-describedby={fieldErrors.avatarUrl ? "avatar-url-error" : "avatar-url-hint"}
                  />
                </label>
                {fieldErrors.avatarUrl ? (
                  <p id="avatar-url-error" className={styles.fieldError}>{fieldErrors.avatarUrl}</p>
                ) : (
                  <p id="avatar-url-hint" className={styles.hint}>{t("avatarUrlHint")}</p>
                )}

                <label>
                  {t("email")}
                  <input name="email" value={profile.email} readOnly aria-describedby="email-hint" />
                </label>
                <p id="email-hint" className={styles.hint}>{t("emailHint")}</p>

                {formError && <p className={styles.formError} role="alert">{formError}</p>}

                <div className={styles.actions}>
                  <button className={styles.submit} type="submit" disabled={pending || !dirty}>
                    {pending ? t("saving") : t("save")}
                  </button>
                  <button
                    className={styles.reset}
                    type="button"
                    disabled={pending || !dirty}
                    onClick={() => { fillForm(profile); setFieldErrors({}); setFormError(""); }}
                  >
                    {t("discard")}
                  </button>
                </div>
              </form>
            </section>
          </>
        )}
      </div>
    </main>
  );
}
