"use client";

import { useEffect, useState, type FormEvent } from "react";
import { useTranslations } from "next-intl";
import { type RecipeDetail, RecipeApiError, saveRecipeIngredient, saveRecipeStep, deleteRecipeContent } from "@/lib/api/recipes";
import styles from "./recipe-draft-form.module.css";

type Kind = "ingredients" | "steps";
type Props = {
  recipe: RecipeDetail;
  accessToken: string;
  disabled: boolean;
  onDirty: (key: string, dirty: boolean) => void;
  mutate: (operation: () => Promise<unknown>) => Promise<boolean>;
};

// Each row is saved through the existing CRUD contract. Other unsaved rows stay mounted.
function ContentRow({ kind, item, count, ...props }: Props & {
  kind: Kind;
  item?: RecipeDetail["ingredients"][number] | RecipeDetail["steps"][number];
  count: number;
}) {
  const t = useTranslations("recipeEditor");
  const isIngredient = kind === "ingredients";
  const initial = isIngredient
    ? { name: item && "name" in item ? item.name : "", quantity: item && "quantity" in item ? String(item.quantity) : "", unit: item && "unit" in item ? item.unit : "", instruction: "", duration: "", imageUrl: "" }
    : { name: "", quantity: "", unit: "", instruction: item && "instruction" in item ? item.instruction : "", duration: item && "durationMinutes" in item ? String(item.durationMinutes ?? "") : "", imageUrl: item && "imageUrl" in item ? item.imageUrl ?? "" : "" };
  const [values, setValues] = useState(initial);
  const [dirty, setDirty] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const key = `${kind}-${item?.id ?? "new"}`;
  const { onDirty } = props;
  useEffect(() => {
    onDirty(key, dirty);
    return () => onDirty(key, false);
  }, [dirty, key, onDirty]);

  function field(name: keyof typeof values, label: string, options: { type?: string; maxLength?: number; min?: string; step?: string } = {}) {
    const inputProps = {
      name, value: values[name], ...options,
      onChange: (event: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => { setValues({ ...values, [name]: event.target.value }); setDirty(true); },
      "aria-invalid": Boolean(errors[name]), "aria-describedby": errors[name] ? `${key}-${name}-error` : undefined,
    };
    return <label>{label}{name === "instruction" ? <textarea {...inputProps} rows={3} /> : <input {...inputProps} />}{errors[name] && <small id={`${key}-${name}-error`} className={styles.fieldError}>{errors[name]}</small>}</label>;
  }

  async function save(event?: FormEvent, order?: number) {
    event?.preventDefault();
    const invalid: Record<string, string> = {};
    if (isIngredient) {
      if (!values.name.trim() || values.name.trim().length > 120) invalid.name = t("ingredientNameError");
      if (!/^\d+(\.\d{1,2})?$/.test(values.quantity) || Number(values.quantity) <= 0 || Number(values.quantity) > 999999.99) invalid.quantity = t("quantityError");
      if (!values.unit.trim() || values.unit.trim().length > 30) invalid.unit = t("unitError");
    } else {
      if (!values.instruction.trim() || values.instruction.trim().length > 2000) invalid.instruction = t("instructionError");
      if (values.duration && (!Number.isSafeInteger(Number(values.duration)) || Number(values.duration) <= 0)) invalid.duration = t("durationError");
      if (values.imageUrl.length > 2048) invalid.imageUrl = t("imageUrlError");
    }
    setErrors(invalid);
    if (Object.keys(invalid).length) return;
    const success = await props.mutate(async () => {
      try {
        if (isIngredient) {
          await saveRecipeIngredient(props.recipe.id, { ingredientName: values.name.trim(), quantity: Number(values.quantity), unit: values.unit.trim(), ...(order !== undefined ? { orderIndex: order } : {}) }, props.accessToken, item?.id);
        } else {
          await saveRecipeStep(props.recipe.id, { instruction: values.instruction.trim(), durationMinutes: values.duration ? Number(values.duration) : null, imageUrl: values.imageUrl.trim() || null, ...(order !== undefined ? { stepNumber: order + 1 } : {}) }, props.accessToken, item?.id);
        }
      } catch (error) {
        if (error instanceof RecipeApiError && error.problem.errors) {
          const aliases: Record<string, string> = { ingredientName: "name", durationMinutes: "duration" };
          setErrors(Object.fromEntries(Object.entries(error.problem.errors).map(([name, messages]) => [aliases[name] ?? name, messages[0]])));
        }
        throw error;
      }
    });
    if (success) { setDirty(false); if (!item) setValues(initial); }
  }

  const index = item ? ("orderIndex" in item ? item.orderIndex : item.stepNumber - 1) : count;
  return (
    <form onSubmit={save} className={styles.contentRow} noValidate>
      <fieldset disabled={props.disabled}>
        <legend>{item ? t("rowNumber", { number: index + 1 }) : t(isIngredient ? "addIngredient" : "addStep")}</legend>
        <div className={isIngredient ? styles.ingredientGrid : styles.form}>
          {isIngredient ? <>{field("name", t("ingredientName"), { maxLength: 120 })}{field("quantity", t("quantity"), { type: "number", min: "0.01", step: "0.01" })}{field("unit", t("unit"), { maxLength: 30 })}</> : <>{field("instruction", t("instruction"), { maxLength: 2000 })}{field("duration", t("duration"), { type: "number", min: "1", step: "1" })}{field("imageUrl", t("stepImageUrl"), { maxLength: 2048 })}</>}
        </div>
        <div className={styles.rowActions}>
          <button type="submit" disabled={Boolean(item) && !dirty}>{t(item ? "saveRow" : "add")}</button>
          {item && <>
            <button type="button" disabled={dirty || index === 0} onClick={() => void save(undefined, index - 1)}>{t("moveUp")}</button>
            <button type="button" disabled={dirty || index >= count - 1} onClick={() => void save(undefined, index + 1)}>{t("moveDown")}</button>
            <button type="button" className={styles.dangerButton} onClick={() => { if (window.confirm(t("deleteRowConfirm"))) void props.mutate(() => deleteRecipeContent(props.recipe.id, kind, item.id, props.accessToken)); }}>{t("remove")}</button>
          </>}
        </div>
      </fieldset>
    </form>
  );
}

export function RecipeContentFields(props: Props) {
  const t = useTranslations("recipeEditor");
  return <>{(["ingredients", "steps"] as const).map((kind) => (
    <section className={styles.section} key={kind} aria-labelledby={`${kind}-editor-title`}>
      <div className={styles.sectionHeading}><div><h2 id={`${kind}-editor-title`}>{t(kind)}</h2><p>{t("rowSaveHint")}</p></div></div>
      {props.recipe[kind].length === 0 && <p className={styles.notice}>{t("emptyRows")}</p>}
      {props.recipe[kind].map((item) => <ContentRow {...props} key={item.id} kind={kind} item={item} count={props.recipe[kind].length} />)}
      <ContentRow {...props} kind={kind} count={props.recipe[kind].length} />
    </section>
  ))}</>;
}
