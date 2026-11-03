import { RecipeDraftForm } from "@/components/recipe-draft-form";

export const metadata = { title: "Edit recipe", robots: { index: false, follow: false } };

export default async function EditRecipePage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  return <RecipeDraftForm key={slug} slug={slug} />;
}
