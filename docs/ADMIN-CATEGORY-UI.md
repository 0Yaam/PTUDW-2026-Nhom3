# Admin and category UI notes

This UI update keeps the existing category API and the Admin role check in the
backend. The dashboard navigation reserves space for future modules, but only
Categories is linked to a working management flow. Other teams can attach their
routes without inheriting placeholder click handlers.

## Visual direction

The design uses a warm ivory canvas, ink sidebar, and restrained copper accents
to connect the Admin dashboard to the food editorial site. It follows the
accessibility and interaction checklist in [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill)
(MIT license): visible focus, larger controls, semantic SVG icons, readable
contrast, responsive layout, and reduced motion support. The public category
cards use the same rounded surfaces and touch targets.

## Category flow

- Admin signs in with the existing auth endpoint. The backend still validates
  the Admin role on every write; the frontend role check is only a UI guard.
- Search filters the loaded categories locally by name, slug, and description.
- Create generates a slug in the API. Rename preserves it; an explicit checkbox
  reveals slug editing and the broken-link warning.
- Delete is available only for an empty category and requires a confirmation.
  The API repeats the recipe-reference check and returns `409` if data changed.
- Loading, empty results, success, RFC 7807 errors, and field errors are shown
  in the page. Copy remains available in Vietnamese and English.

The page keeps access tokens in component memory. Reloading it requires a new
sign-in; do not store tokens in a new browser persistence mechanism without the
team's auth review.
