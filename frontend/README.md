# Culinary Blog Web App

This folder contains the Next.js App Router frontend. Use the root [README](../README.md) for setup and test commands.

The Agent Bootstrap includes a category page with loading, empty, and error states.

The shared visual design follows Han's selected food website reference with
project-owned imagery, a responsive theme, and reusable page sections. See
[the theme notes](../docs/UI-THEME-FOOD-WEBSITE.md) for provenance, SRS fit,
and integration boundaries.

Issue #2 adds `/admin/categories`. Sign in with an existing Admin account,
then create categories or select one to edit its name and description. The page
shows validation, permission, network, loading, empty, and save states. Its
access token stays in page memory and is cleared on sign-out or an unauthorized
save; a reload requires sign-in again. The API checks Admin permission for every
write. Category reads use `cache: "no-store"` so an Admin
edit appears on the next public request.

To test locally with the default Compose database, register on the homepage
first. Registration creates an Author. For **local development only**, a team
member with access to the development database can assign the Admin role to
that specific account:

```powershell
docker compose exec -T postgres psql -U culinary -d culinary_blog -c "UPDATE users SET role='Admin' WHERE email='your-email@example.com';"
```

Check for `UPDATE 1`, then sign in at `/admin/categories`. Use your configured
PostgreSQL user/database values if they differ from Compose defaults. This is
manual local setup; the application has no role-granting endpoint or production
development helper.
