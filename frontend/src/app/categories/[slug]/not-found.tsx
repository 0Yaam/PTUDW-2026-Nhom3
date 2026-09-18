import Link from "next/link";

export default function CategoryNotFound() {
  return (
    <main className="error-shell">
      <p className="eyebrow">Not found</p>
      <h1>This category is not on the menu.</h1>
      <p>The link may be old, or the category was renamed.</p>
      <Link className="primary-action" href="/#categories">
        Browse categories
      </Link>
    </main>
  );
}
