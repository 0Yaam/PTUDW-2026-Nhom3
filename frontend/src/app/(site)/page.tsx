import Image from "next/image";
import { getTranslations } from "next-intl/server";
import { AuthPanel } from "@/components/auth-panel";
import { CategoryGrid } from "@/components/category-grid";
import { getCategories } from "@/lib/api/categories";

export const dynamic = "force-dynamic";

const previewDishes = ["/images/vietnamese-table.png", "/images/breakfast.png", "/images/plant-based.png", "/images/dessert.png"];

export default async function Home() {
  const [categories, t] = await Promise.all([getCategories(), getTranslations("home")]);

  return (
    <main id="main-content">
      <section className="hero" aria-labelledby="hero-title">
        <div className="hero-inner">
          <div className="hero-collage" aria-hidden="true">
            {previewDishes.map((dish, index) => (
              <div className={`hero-dish hero-dish-${index + 1}`} key={dish}>
                <Image src={dish} alt="" fill priority={index === 0} sizes="(max-width: 800px) 45vw, 28vw" />
              </div>
            ))}
          </div>
          <div className="hero-copy">
            <p className="eyebrow">{t("heroEyebrow")} <span aria-hidden="true">✳</span> Est. 2026</p>
            <h1 id="hero-title">{t("heroTitle1")}<br /><span>{t("heroTitle2")}</span></h1>
            <p className="lead">{t("heroDescription")}</p>
            <div className="hero-actions">
              <a className="primary-action" href="#categories">{t("explore")} <span aria-hidden="true">↗</span></a>
              <a className="text-action" href="#about">{t("knowUs")} <span aria-hidden="true">→</span></a>
            </div>
            <div className="hero-social-proof"><span className="proof-stars" aria-hidden="true">✳ ✳ ✳</span><span>{t("heroProof")}</span></div>
          </div>
        </div>
        <div className="hero-bottom" aria-hidden="true"><span>{t("ribbonDiscover")}</span><span>{t("ribbonCook")}</span><span>{t("ribbonShare")}</span><span>{t("ribbonEnjoy")}</span></div>
      </section>

      <section className="category-section" id="categories" aria-labelledby="categories-title">
        <div className="section-heading"><div><p className="eyebrow">{t("categoryEyebrow")}</p><h2 id="categories-title">{t("categoryTitle1")} <em>{t("categoryTitle2")}</em></h2></div><p>{t("categoryDescription")}</p></div>
        <CategoryGrid categories={categories} />
        <p className="section-footnote">{t("categoryTotal", { count: categories.length })}</p>
      </section>

      <section className="story" id="about" aria-labelledby="story-title">
        <div className="story-visual" aria-hidden="true">{previewDishes.map((dish, index) => <div className="story-dish" key={dish}><Image src={dish} alt="" fill sizes="(max-width: 560px) 42vw, 220px" /><span>{String(index + 1).padStart(2, "0")}</span></div>)}</div>
        <div className="story-content"><p className="eyebrow">{t("storyEyebrow")}</p><h2 id="story-title">{t("storyTitle1")} <em>{t("storyTitle2")}</em></h2><p>{t("storyParagraph1")}</p><p>{t("storyParagraph2")}</p><a className="primary-action" href="#auth">{t("join")} <span aria-hidden="true">↗</span></a></div>
      </section>

      <AuthPanel />
    </main>
  );
}
