import { RecipeDetailView } from "@/components/recipe-detail-view";

export default async function RecipeDetailPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = await params;
  return <RecipeDetailView slug={slug} />;
}
