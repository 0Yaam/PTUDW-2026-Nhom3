import type { Metadata } from "next";
import { RecipeEditForm } from "@/components/recipe-edit-form";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default async function EditRecipePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <RecipeEditForm slug={slug} />;
}
