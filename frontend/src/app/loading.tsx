import { getTranslations } from "next-intl/server";

export default async function Loading() {
  const t = await getTranslations("status");
  return (
    <main id="main-content" className="loading-shell" aria-busy="true" aria-label={t("loading")}>
      <div className="loading-line short" />
      <div className="loading-line title" />
      <div className="loading-line" />
      <div className="loading-cards">
        {[0, 1, 2, 3].map((item) => <div className="loading-card" key={item} />)}
      </div>
    </main>
  );
}
