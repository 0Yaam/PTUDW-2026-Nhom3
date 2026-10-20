import Link from "next/link";
import { getTranslations } from "next-intl/server";

import styles from "./not-found.module.css";

export default async function NotFound() {
  const t = await getTranslations("notFound");

  return (
    <main id="main-content" className={styles.page}>
      <section className={styles.panel} aria-labelledby="not-found-title">
        <p className={styles.code} aria-hidden="true">404</p>
        <div className={styles.content}>
          <p className={styles.eyebrow}>{t("eyebrow")}</p>
          <h1 id="not-found-title">{t("title")}</h1>
          <p className={styles.description}>{t("description")}</p>
          <nav className={styles.actions} aria-label={t("navigation")}>
            <Link className={styles.primary} href="/">{t("home")}</Link>
            <Link className={styles.secondary} href="/recipes">{t("recipes")}</Link>
          </nav>
        </div>
      </section>
    </main>
  );
}
