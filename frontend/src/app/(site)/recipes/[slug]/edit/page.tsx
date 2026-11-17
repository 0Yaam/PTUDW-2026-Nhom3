import type { Metadata } from "next";
import { getTranslations } from "next-intl/server";

import { RecipeDraftForm } from "@/components/recipe-draft-form";

export async function generateMetadata(): Promise<Metadata> {
  const t = await getTranslations("recipeEditor");
  return { title: t("editPageTitle"), robots: { index: false, follow: false } };
}

export default async function EditRecipePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <RecipeDraftForm key={slug} slug={slug} />;
}
