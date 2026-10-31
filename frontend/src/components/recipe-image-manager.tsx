"use client";

import Image from "next/image";
import { FormEvent, useState } from "react";
import { useTranslations } from "next-intl";
import {
  RecipeApiError,
  deleteRecipeImage,
  replaceRecipeImage,
  setPrimaryRecipeImage,
  uploadRecipeImage,
  type RecipeImage,
} from "@/lib/api/recipes";
import { clearAuthSession } from "@/lib/auth-session";
import styles from "./recipe-image-manager.module.css";

const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
const ALLOWED_TYPES = new Set(["image/jpeg", "image/png", "image/webp", "image/avif"]);
const ACCEPT = "image/jpeg,image/png,image/webp,image/avif";

type Props = {
  recipeId: string;
  recipeTitle: string;
  images: RecipeImage[];
  accessToken: string;
  onChanged: () => void;
};

export function RecipeImageManager({ recipeId, recipeTitle, images, accessToken, onChanged }: Props) {
  const t = useTranslations("recipeImages");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [replacementFiles, setReplacementFiles] = useState<Record<string, File>>({});
  const [pending, setPending] = useState(false);
  const [fileInputVersion, setFileInputVersion] = useState(0);
  const [confirmDeleteId, setConfirmDeleteId] = useState<string | null>(null);
  const [error, setError] = useState("");

  function validate(file: File | null): boolean {
    if (!file) {
      setError(t("chooseFile"));
      return false;
    }
    if (!ALLOWED_TYPES.has(file.type)) {
      setError(t("invalidType"));
      return false;
    }
    if (file.size === 0 || file.size > MAX_IMAGE_BYTES) {
      setError(t("invalidSize"));
      return false;
    }
    return true;
  }

  async function run(action: () => Promise<unknown>) {
    setPending(true);
    setError("");
    try {
      await action();
      setUploadFile(null);
      setReplacementFiles({});
      setFileInputVersion((version) => version + 1);
      setConfirmDeleteId(null);
      onChanged();
    } catch (caught) {
      if (caught instanceof RecipeApiError && caught.status === 401) clearAuthSession();
      setError(caught instanceof RecipeApiError
        ? caught.problem.detail ?? t("requestFailed")
        : t("requestFailed"));
    } finally {
      setPending(false);
    }
  }

  function submitUpload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (pending || !validate(uploadFile)) return;
    const file = uploadFile!;
    void run(() => uploadRecipeImage(recipeId, file, accessToken));
  }

  return (
    <section className={styles.manager} aria-labelledby="recipe-images-manager-title">
      <div className={styles.heading}>
        <h2 id="recipe-images-manager-title">{t("title")}</h2>
        <p>{t("hint")}</p>
      </div>
      {error && <p className={styles.error} role="alert">{error}</p>}
      <form className={styles.upload} onSubmit={submitUpload}>
        <div className={styles.fileSelection}>
          <div className={styles.picker}>
            <input
              key={fileInputVersion}
              className={styles.fileInput}
              id="recipe-image-upload"
              type="file"
              accept={ACCEPT}
              disabled={pending}
              onChange={(event) => {
                setUploadFile(event.target.files?.[0] ?? null);
                setError("");
              }}
            />
            <label className={styles.chooseButton} htmlFor="recipe-image-upload">{t("addImage")}</label>
          </div>
          <span className={styles.fileName} aria-live="polite" title={uploadFile?.name}>
            {uploadFile?.name ?? t("noFileSelected")}
          </span>
        </div>
        <button className={styles.uploadButton} type="submit" disabled={pending || !uploadFile}>
          {pending ? t("saving") : t("upload")}
        </button>
      </form>
      {images.length === 0 ? <p className={styles.empty}>{t("noImages")}</p> : (
        <ul className={styles.list}>
          {images.map((image, index) => (
            <li key={image.id} className={styles.item}>
              <Image
                className={styles.thumbnail}
                src={image.thumbnailUrl ?? image.originalUrl}
                alt={image.altText ?? recipeTitle}
                width={84}
                height={70}
                unoptimized
              />
              <div className={styles.details}>
                <strong>{t("imageNumber", { number: index + 1 })}</strong>
                {image.isPrimary && <span className={styles.primary}>{t("primary")}</span>}
                <div className={styles.picker}>
                  <input
                    key={fileInputVersion}
                    className={styles.fileInput}
                    id={`replace-${image.id}`}
                    type="file"
                    accept={ACCEPT}
                    disabled={pending}
                    onChange={(event) => {
                      const file = event.target.files?.[0];
                      setError("");
                      setReplacementFiles((current) => {
                        const next = { ...current };
                        if (file) next[image.id] = file;
                        else delete next[image.id];
                        return next;
                      });
                    }}
                  />
                  <label className={styles.chooseButton} htmlFor={`replace-${image.id}`}>
                    {t("replacementFile")}
                  </label>
                </div>
                <span className={styles.fileName} aria-live="polite" title={replacementFiles[image.id]?.name}>
                  {replacementFiles[image.id]?.name ?? t("noFileSelected")}
                </span>
              </div>
              <div className={styles.actions}>
                <button
                  type="button"
                  disabled={pending || !replacementFiles[image.id]}
                  onClick={() => {
                    const file = replacementFiles[image.id];
                    if (pending || !validate(file)) return;
                    void run(() => replaceRecipeImage(recipeId, image.id, file, accessToken));
                  }}
                >{t("replace")}</button>
                {!image.isPrimary && (
                  <button
                    type="button"
                    disabled={pending}
                    onClick={() => { if (!pending) void run(() => setPrimaryRecipeImage(recipeId, image.id, accessToken)); }}
                  >{t("makePrimary")}</button>
                )}
                {confirmDeleteId === image.id ? (
                  <span className={styles.confirm}>
                    <span>{t("confirmDelete")}</span>
                    <button type="button" disabled={pending} onClick={() => { if (!pending) void run(() => deleteRecipeImage(recipeId, image.id, accessToken)); }}>{t("confirm")}</button>
                    <button type="button" disabled={pending} onClick={() => setConfirmDeleteId(null)}>{t("cancel")}</button>
                  </span>
                ) : (
                  <button type="button" disabled={pending} onClick={() => setConfirmDeleteId(image.id)}>{t("delete")}</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
