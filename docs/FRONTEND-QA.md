# Frontend QA: Accessibility, SEO, Performance

Final QA record for the public frontend, covering NFR-USE-001 to NFR-USE-004,
NFR-PERF-005, NFR-SEO-001 to NFR-SEO-004, and NFR-MAINT-003 to NFR-MAINT-004.
Issues [#46](https://github.com/0Yaam/PTUDW-2026-Nhom3/issues/46) (Cycle 3)
and [#60](https://github.com/0Yaam/PTUDW-2026-Nhom3/issues/60) (Cycle 4).

Pages in scope: `/`, `/recipes`, `/recipes/[slug]`, `/recipes/new`,
`/categories/[slug]`, `/profile`.

## Accessibility

| Check | Result | Where |
|---|---|---|
| Skip link as first focusable element | Pass | `site-header.tsx`, `.skip-link` in `globals.css` |
| Single `<main id="main-content">` per page | Pass | every page and the `loading` / `error` boundaries |
| Visible focus ring on every control | Pass | `:focus-visible` outline in `globals.css` |
| Landmarks labelled (`nav`, `section`) | Pass | header, mobile nav, footer, page sections |
| Headings in order, one `<h1>` per page | Pass | all pages in scope |
| Non-text content either labelled or hidden | Pass | decorative glyphs use `aria-hidden`, images carry `alt` |
| Fields have a real label, required marked in text | Pass | draft form, profile form, auth panel |
| Errors linked with `aria-invalid` + `aria-describedby` | Pass | draft form, profile form |
| Focus moves to the first rejected field | Pass | `lib/form-errors.ts`, used by both forms |
| Error and status text never relies on colour alone | Pass | all states carry words |
| Loading, empty, and error states announced | Pass | `aria-busy`, `aria-live`, `role="alert"` |
| Menus and disclosures keyboard operable | Pass | native `<details>`, `aria-expanded` on toggles |
| Interface text and ARIA labels translated | Pass | `messages/en.json` and `messages/vi.json`, same key set |
| Responsive from 320 px to desktop | Pass | fluid `width: min(100% - …, …)` shells, no fixed pixel pages |

Fixed in Cycle 4 (#60):

- `aria-label="Account action"`, `"Footer navigation"`, and
  `"Small Kitchen home"` were hardcoded English on a bilingual site. Now served
  from `nav.footer`, `nav.brandHome`, and `auth.modeLabel`.
- Rejecting a form left focus where it was, so keyboard and screen reader users
  had to search for the problem. Both forms now call `focusFirstInvalidField`,
  for client-side validation and for a `422` from the API.
- The auth panel form was not associated with its message area; it now points
  at it with `aria-describedby`.

Verified by code audit over the files above plus the key-parity check
(`en.json` and `vi.json` expose the same keys). A browser pass with a real
screen reader was not part of this QA; the manual keyboard route to repeat
before a release is in [USER-GUIDE.md](USER-GUIDE.md#keyboard-and-screen-reader-notes).

## SEO

| Check | Result | Where |
|---|---|---|
| `metadataBase` and title template | Pass | `app/layout.tsx` |
| Locale-aware default description | Pass | `app/layout.tsx` |
| Canonical URL on every public page | Pass | home, `/recipes`, recipe detail, category detail |
| Per-page title and description | Pass | same |
| Open Graph on recipe detail | Pass | `recipes/[slug]/page.tsx` |
| `Recipe` structured data (ingredients, steps, nutrition) | Pass | `recipes/[slug]/page.tsx` |
| `CollectionPage` + `ItemList` structured data | Pass | `categories/[slug]/page.tsx` |
| Missing recipe or category returns `noindex` | Pass | both `generateMetadata` functions |
| Private pages `noindex` | Pass | `/profile`, `/recipes/new` |
| Sitemap lists public content only | Pass | `app/sitemap.ts` uses `listPublishedRecipes()` |
| `robots.txt` points at the sitemap, disallows private paths | Pass | `app/robots.ts` |
| Slug-based, human-readable URLs | Pass | `/recipes/<slug>`, `/categories/<slug>` |

Fixed while closing #46, shipped separately:

- `/recipes` had no metadata at all and was missing from the sitemap. It now
  carries a translated title and description, a canonical URL, and a sitemap
  entry at `changeFrequency: "daily"`. That fix belongs to issue #46 and is in
  its own pull request, so the two rows above only hold once it is merged.

Both `sitemap.xml` and `robots.txt` resolve against `APP_PUBLIC_URL`
(`lib/site-url.ts`), so a deployment only needs that one variable set to emit
correct absolute URLs. Left at its `http://localhost:3000` default, the sitemap
URLs point at localhost — set it in production.

## Performance

No regression found; no new dependency was added for this work. The frontend
still ships only `next`, `react`, `react-dom`, and `next-intl`.

| Aspect | State |
|---|---|
| Fonts | System stacks only (`Segoe UI` / `Georgia` fallbacks). Zero font requests, so no FOUT and no font budget to blow. |
| Local images | `next/image` with explicit `sizes`, so each viewport downloads one correctly sized variant. |
| Hero image | `priority` on the first collage tile only; the rest stay lazy. |
| Remote images | Recipe photos come from MinIO and are served `unoptimized`: the resize job (#47) produces the variants instead of the Next.js optimizer, which would otherwise need `remotePatterns` for every bucket host. |
| Avatar | Plain `<img>` with fixed `width`/`height` — arbitrary user URLs, so no optimizer config, and no layout shift. |
| CSS | One 339-line global sheet plus CSS modules per component. No UI framework. |
| Client JS | Server Components by default; `"use client"` only where there is state (auth panel, forms, lists, locale switch). |
| Data | `cache: "no-store"` for lists that must be fresh. Reads are paginated 12 per page, never unbounded. |

Known ceilings, deliberate:

- The recipe list fetches categories and results in two requests on mount; one
  combined endpoint would save a round trip. Not worth a new endpoint at this
  size.
- Lighthouse and Core Web Vitals numbers were not captured — the measurement
  needs a deployed origin with real images, not `localhost` placeholders. Run
  it against staging once `APP_PUBLIC_URL` is live.

## Checks

```bash
cd frontend
npm run lint      # clean
npx tsc --noEmit  # clean
npm run build     # succeeds, 10 routes generated
```

All three pass as of this change.
