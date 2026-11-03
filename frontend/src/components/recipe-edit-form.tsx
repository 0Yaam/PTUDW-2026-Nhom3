"use client";

import Link from "next/link";
import { FormEvent, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import type { Category } from "@/components/category-grid";
import { getCategories } from "@/lib/api/categories";
import { createRecipeIngredient, createRecipeStep, deleteRecipeIngredient, deleteRecipeStep, getRecipeDetail, updateRecipe, updateRecipeIngredient, updateRecipeStep, type RecipeDetail, type RecipeDraftInput } from "@/lib/api/recipes";
import { useAuthStore } from "@/lib/auth-store";
import styles from "./recipe-draft-form.module.css";

export function RecipeEditForm({ slug }: { slug: string }) {
  const t = useTranslations("recipeForm");
  const session = useAuthStore();
  const [recipe, setRecipe] = useState<RecipeDetail | null>(null);
  const [categories, setCategories] = useState<Category[]>([]);
  const [loading, setLoading] = useState(true);
  const [pending, setPending] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [ingredients, setIngredients] = useState<RecipeDetail["ingredients"]>([]);
  const [steps, setSteps] = useState<RecipeDetail["steps"]>([]);
  const [removedIngredients, setRemovedIngredients] = useState<string[]>([]);
  const [removedSteps, setRemovedSteps] = useState<string[]>([]);

  useEffect(() => { let active = true; if (!session) return () => { active = false; }; void Promise.all([getRecipeDetail(slug, session.accessToken), getCategories()]).then(([detail, categoryList]) => { if (active) { setRecipe(detail); setIngredients(detail.ingredients); setSteps(detail.steps); setCategories(categoryList); } }).catch(() => { if (active) setError(t("apiUnavailable")); }).finally(() => { if (active) setLoading(false); }); return () => { active = false; }; }, [session, slug, t]);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); if (!session || !recipe) return; setPending(true); setError(""); setMessage("");
    const data = new FormData(event.currentTarget);
    const input: RecipeDraftInput & { rowVersion: string } = { title: String(data.get("title") ?? "").trim(), description: String(data.get("description") ?? "").trim(), categoryId: String(data.get("categoryId") ?? ""), prepTimeMinutes: Number(data.get("prepTimeMinutes")), cookTimeMinutes: Number(data.get("cookTimeMinutes")), servings: Number(data.get("servings")), difficulty: Number(data.get("difficulty")), instructions: String(data.get("instructions") ?? "").trim(), rowVersion: recipe.rowVersion };
    try {
      const updated = await updateRecipe(recipe.id, input, session.accessToken);
      await Promise.all([
        ...ingredients.filter((item) => item.name.trim()).map((item, index) => item.id
          ? updateRecipeIngredient(recipe.id, item.id, { ingredientName: item.name.trim(), quantity: Number(item.quantity), unit: item.unit.trim(), orderIndex: index }, session.accessToken)
          : createRecipeIngredient(recipe.id, { ingredientName: item.name.trim(), quantity: Number(item.quantity), unit: item.unit.trim() }, session.accessToken)),
        ...steps.filter((item) => item.instruction.trim()).map((item, index) => item.id
          ? updateRecipeStep(recipe.id, item.id, { instruction: item.instruction.trim(), stepNumber: index + 1 }, session.accessToken)
          : createRecipeStep(recipe.id, { instruction: item.instruction.trim(), stepNumber: index + 1 }, session.accessToken)),
        ...removedIngredients.map((id) => deleteRecipeIngredient(recipe.id, id, session.accessToken)),
        ...removedSteps.map((id) => deleteRecipeStep(recipe.id, id, session.accessToken)),
      ]);
      setRemovedIngredients([]); setRemovedSteps([]);
      setRecipe((current) => current ? { ...current, title: updated.title, description: updated.description, instructions: updated.instructions, categoryId: updated.categoryId, prepTimeMinutes: updated.prepTimeMinutes, cookTimeMinutes: updated.cookTimeMinutes, servings: updated.servings, difficulty: updated.difficulty, rowVersion: updated.rowVersion, status: updated.status, category: categories.find((item) => item.id === updated.categoryId) ?? current.category } : current);
      setMessage(t("updated"));
    } catch { setError(t("requestFailed")); } finally { setPending(false); }
  }

  if (session === undefined || loading) return <main className={styles.page}><div className={styles.centerState}>{t("checkingSession")}</div></main>;
  if (!session) return <main className={styles.page}><div className={styles.centerState}><h1>{t("signInTitle")}</h1><Link href="/#auth">{t("signIn")}</Link></div></main>;
  if (!recipe) return <main className={styles.page}><div className={styles.centerState}><p>{error || t("apiUnavailable")}</p></div></main>;
  return <main className={styles.page}><div className={styles.shell}><Link className={styles.backLink} href={`/recipes/${recipe.slug}`}>← {t("back")}</Link><header className={styles.pageHeader}><div><p className={styles.eyebrow}>EDIT RECIPE</p><h1>{recipe.title}</h1><p className={styles.intro}>{recipe.status}</p></div><span className={styles.draftBadge}>{recipe.status}</span></header><form className={styles.form} onSubmit={submit} noValidate>{message && <p className={styles.successBanner} role="status">{message}</p>}{error && <p className={styles.formError} role="alert">{error}</p>}<section className={styles.section}><label>{t("recipeTitle")}<input name="title" defaultValue={recipe.title} required minLength={5} maxLength={200} /></label><label>{t("recipeDescription")}<textarea name="description" defaultValue={recipe.description} rows={4} required /></label><label>{t("category")}<select name="categoryId" defaultValue={recipe.category.id}>{categories.map((category) => <option key={category.id} value={category.id}>{category.name}</option>)}</select></label></section><section className={styles.section}><div className={styles.numberGrid}><label>{t("prepTime")}<input name="prepTimeMinutes" type="number" min="1" defaultValue={recipe.prepTimeMinutes} required /></label><label>{t("cookTime")}<input name="cookTimeMinutes" type="number" min="0" defaultValue={recipe.cookTimeMinutes} required /></label><label>{t("servings")}<input name="servings" type="number" min="1" defaultValue={recipe.servings} required /></label></div><label>{t("difficulty")}<select name="difficulty" defaultValue={String(recipe.difficulty)}>{[1,2,3,4].map((value) => <option key={value} value={value}>{t(`difficulty${value}`)}</option>)}</select></label></section><section className={styles.section}><h2>Ingredients</h2>{ingredients.map((item,index)=><div className={styles.numberGrid} key={item.id || `ingredient-${index}`}><input aria-label="Ingredient name" value={item.name} onChange={(e)=>setIngredients((all)=>all.map((current,i)=>i===index?{...current,name:e.target.value}:current))}/><input aria-label="Quantity" type="number" min="0.01" value={item.quantity} onChange={(e)=>setIngredients((all)=>all.map((current,i)=>i===index?{...current,quantity:Number(e.target.value)}:current))}/><input aria-label="Unit" value={item.unit} onChange={(e)=>setIngredients((all)=>all.map((current,i)=>i===index?{...current,unit:e.target.value}:current))}/><button type="button" onClick={()=>{if(item.id)setRemovedIngredients((all)=>[...all,item.id]);setIngredients((all)=>all.filter((_,i)=>i!==index));}}>×</button></div>)}<button type="button" onClick={()=>setIngredients((all)=>[...all,{id:"",ingredientId:"",name:"",quantity:1,unit:"",orderIndex:all.length}])}>+ Add ingredient</button></section><section className={styles.section}><h2>Steps</h2>{steps.map((item,index)=><div key={item.id || `step-${index}`}><textarea aria-label={`Step ${index+1}`} rows={3} value={item.instruction} onChange={(e)=>setSteps((all)=>all.map((current,i)=>i===index?{...current,instruction:e.target.value}:current))}/><button type="button" onClick={()=>{if(item.id)setRemovedSteps((all)=>[...all,item.id]);setSteps((all)=>all.filter((_,i)=>i!==index));}}>Remove step</button></div>)}<button type="button" onClick={()=>setSteps((all)=>[...all,{id:"",recipeId:recipe.id,stepNumber:all.length+1,instruction:"",durationMinutes:null,imageUrl:null}])}>+ Add step</button></section><section className={styles.section}><label>{t("instructions")}<textarea name="instructions" defaultValue={recipe.instructions} rows={8} /></label></section><button className={styles.submit} type="submit" disabled={pending}>{pending ? t("saving") : t("save")}</button></form></div></main>;
}
