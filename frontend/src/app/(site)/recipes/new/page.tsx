import type { Metadata } from "next";
import { RecipeDraftForm } from "@/components/recipe-draft-form";

export const metadata: Metadata = { robots: { index: false, follow: false } };

export default function NewRecipePage() {
  return <RecipeDraftForm />;
}
