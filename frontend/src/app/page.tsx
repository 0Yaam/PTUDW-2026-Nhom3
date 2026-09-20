import Image from "next/image";
import { AuthPanel } from "@/components/auth-panel";
import { CategoryGrid } from "@/components/category-grid";
import { getCategories } from "@/lib/api/categories";

export const dynamic = "force-dynamic";

const previewDishes = ["/images/vietnamese-table.png", "/images/breakfast.png", "/images/plant-based.png", "/images/dessert.png"];

export default async function Home() {
  const categories = await getCategories();

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
            <p className="eyebrow">Your kitchen, your story <span aria-hidden="true">✳</span> Est. 2026</p>
            <h1 id="hero-title">Your favorite food.<br /><span>Make it good.</span></h1>
            <p className="lead">Discover the dishes you love, explore new flavors, and share the joy of cooking at home.</p>
            <div className="hero-actions">
              <a className="primary-action" href="#categories">Explore the kitchen <span aria-hidden="true">↗</span></a>
              <a className="text-action" href="#about">Get to know us <span aria-hidden="true">→</span></a>
            </div>
            <div className="hero-social-proof"><span className="proof-stars" aria-hidden="true">✳ ✳ ✳</span><span>Good things happen around food</span></div>
          </div>
        </div>
        <div className="hero-bottom" aria-hidden="true"><span>DISCOVER</span><span>COOK</span><span>SHARE</span><span>ENJOY</span></div>
      </section>

      <section className="category-section" id="categories" aria-labelledby="categories-title">
        <div className="section-heading"><div><p className="eyebrow">Explore the kitchen</p><h2 id="categories-title">Find your next <em>favorite.</em></h2></div><p>Every great meal starts somewhere. Browse real categories from our kitchen and find the flavors that speak to you.</p></div>
        <CategoryGrid categories={categories} />
        <p className="section-footnote">{categories.length} {categories.length === 1 ? "category" : "categories"} to explore</p>
      </section>

      <section className="story" id="about" aria-labelledby="story-title">
        <div className="story-visual" aria-hidden="true">{previewDishes.map((dish, index) => <div className="story-dish" key={dish}><Image src={dish} alt="" fill sizes="(max-width: 560px) 42vw, 220px" /><span>{String(index + 1).padStart(2, "0")}</span></div>)}</div>
        <div className="story-content"><p className="eyebrow">The story behind the plate</p><h2 id="story-title">A kitchen for <em>everybody.</em></h2><p>Food has a way of bringing people together. Small Kitchen is a space to explore flavors, learn from one another, and celebrate what we make at home.</p><p>Our recipe collection is growing with the team. Start with the categories and join the kitchen today.</p><a className="primary-action" href="#auth">Join the kitchen <span aria-hidden="true">↗</span></a></div>
      </section>

      <AuthPanel />
    </main>
  );
}
