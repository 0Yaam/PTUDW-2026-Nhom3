import { CategoryGrid } from "@/components/category-grid";
import { getCategories } from "@/lib/api/categories";

export const dynamic = "force-dynamic";

export default async function Home() {
  const categories = await getCategories();

  return (
    <main>
      <section className="hero">
        <nav className="nav" aria-label="Main navigation">
          <a className="brand" href="#top" aria-label="Small Kitchen home">
            <span className="brand-mark">SK</span>
            <span>Small Kitchen</span>
          </a>
          <div className="nav-links">
            <a href="#categories">Categories</a>
            <a href="#story">Our start</a>
            <span className="soon">Recipes - coming soon</span>
          </div>
        </nav>

        <div className="hero-grid" id="top">
          <div className="hero-copy">
            <p className="eyebrow">Culinary Blog / Team 3</p>
            <h1>
              <span>Cook a meal,</span>
              <span>share the story,</span>
              <em>keep the memory.</em>
            </h1>
            <p className="lead">
              A simple place for clear recipes, useful cooking notes, and food stories
              from real home kitchens.
            </p>
            <a className="primary-action" href="#categories">
              Browse categories <span aria-hidden="true">-&gt;</span>
            </a>
          </div>

          <div className="hero-art" aria-hidden="true">
            <div className="sun" />
            <div className="plate">
              <div className="leaf leaf-one" />
              <div className="leaf leaf-two" />
              <div className="noodle noodle-one" />
              <div className="noodle noodle-two" />
              <div className="noodle noodle-three" />
            </div>
            <p className="art-note">One season, one taste<br />One home, one kitchen</p>
          </div>
        </div>
      </section>

      <section className="category-section" id="categories">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Live database data</p>
            <h2>What should we cook today?</h2>
          </div>
          <p>
            These categories come from PostgreSQL through FastAPI. The seed command is
            safe to run more than once.
          </p>
        </div>
        <CategoryGrid categories={categories} />
      </section>

      <section className="story" id="story">
        <span className="story-number">01</span>
        <div>
          <p className="eyebrow">Agent Bootstrap</p>
          <h2>Start small and make it work.</h2>
        </div>
        <p>
          This first slice connects a migration, safe seed data, an API, a page, and
          tests. The students will build the remaining features through their own
          Issues and Pull Requests.
        </p>
      </section>
    </main>
  );
}
