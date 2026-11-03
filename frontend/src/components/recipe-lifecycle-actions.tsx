"use client";

import Link from "next/link";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { archiveRecipe, deleteRecipe, publishRecipe, unpublishRecipe, type RecipeDetail } from "@/lib/api/recipes";
import styles from "./recipe-lifecycle-actions.module.css";

export function RecipeLifecycleActions({ recipe, accessToken, onChanged }: { recipe: RecipeDetail; accessToken: string; onChanged: () => void }) {
  const t = useTranslations("recipeDetail");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const run = async (action: () => Promise<unknown>) => { setBusy(true); setError(""); try { await action(); onChanged(); } catch { setError(t("lifecycleError")); } finally { setBusy(false); } };
  return <section className={styles.panel} aria-label={t("lifecycleTitle")}>
    <div><p className={styles.kicker}>{t("lifecycleKicker")}</p><h2>{t("lifecycleTitle")}</h2><p>{t(`status${recipe.status}`)}</p></div>
    <div className={styles.actions}>
      <Link href={`/recipes/${recipe.slug}/edit`} className={styles.edit}>{t("editRecipe")}</Link>
      {recipe.status === "Draft" && <button disabled={busy} onClick={() => void run(() => publishRecipe(recipe.id, accessToken))}>{t("publish")}</button>}
      {recipe.status === "Published" && <button disabled={busy} onClick={() => void run(() => unpublishRecipe(recipe.id, accessToken))}>{t("unpublish")}</button>}
      {recipe.status !== "Archived" && <button disabled={busy} onClick={() => void run(() => archiveRecipe(recipe.id, accessToken))}>{t("archive")}</button>}
      <button className={styles.danger} disabled={busy} onClick={() => { if (window.confirm(t("deleteConfirm"))) void run(() => deleteRecipe(recipe.id, accessToken)); }}>{t("delete")}</button>
    </div>
    {error && <p className={styles.error} role="alert">{error}</p>}
  </section>;
}
