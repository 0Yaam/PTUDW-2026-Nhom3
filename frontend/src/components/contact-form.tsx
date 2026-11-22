"use client";

import { FormEvent, useState } from "react";
import { useTranslations } from "next-intl";

import { ApiError } from "@/lib/api/client";
import { submitContact } from "@/lib/api/contact";

import styles from "./contact-form.module.css";

export function ContactForm() {
  const t = useTranslations("contact");
  const errorT = useTranslations("errors");
  const [pending, setPending] = useState(false);
  const [success, setSuccess] = useState(false);
  const [message, setMessage] = useState("");

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const data = new FormData(form);
    setPending(true);
    setMessage("");
    try {
      await submitContact({
        fullName: String(data.get("fullName") ?? ""),
        email: String(data.get("email") ?? ""),
        message: String(data.get("message") ?? ""),
      });
      form.reset();
      setSuccess(true);
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

  return (
    <main className={styles.page} id="main-content">
      <div className={styles.layout}>
        <header className={styles.intro}>
          <p className="eyebrow">{t("eyebrow")}</p>
          <h1>{t("title")}</h1>
          <p className={styles.lead}>{t("description")}</p>
          <section className={styles.guidance} aria-labelledby="contact-guidance-title">
            <h2 id="contact-guidance-title">{t("guidanceTitle")}</h2>
            <ul>
              <li>{t("guidanceEmail")}</li>
              <li>{t("guidanceSensitive")}</li>
              <li>{t("guidanceLimit")}</li>
            </ul>
          </section>
        </header>

        <section className={styles.formSurface} aria-labelledby="contact-form-title">
          <h2 id="contact-form-title">{success ? t("successTitle") : t("formTitle")}</h2>
          {success ? (
            <div className={styles.success} role="status">
              <p>{t("successDescription")}</p>
              <button type="button" onClick={() => setSuccess(false)}>
                {t("sendAnother")}
              </button>
            </div>
          ) : (
            <form onSubmit={submit} aria-describedby="contact-form-note contact-message">
              <p className={styles.formNote} id="contact-form-note">
                {t("requiredNote")}
              </p>
              <label>
                {t("fullName")}
                <input
                  name="fullName"
                  autoComplete="name"
                  minLength={2}
                  maxLength={150}
                  required
                />
              </label>
              <label>
                {t("email")}
                <input name="email" type="email" autoComplete="email" maxLength={320} required />
              </label>
              <label>
                {t("message")}
                <textarea name="message" rows={8} minLength={10} maxLength={4000} required />
              </label>
              <p className={styles.messageHint}>{t("messageHint")}</p>
              <p className={styles.error} id="contact-message" role={message ? "alert" : undefined}>
                {message}
              </p>
              <button className={styles.submit} type="submit" disabled={pending}>
                {pending ? t("sending") : t("send")}
              </button>
            </form>
          )}
        </section>
      </div>
    </main>
  );
}
