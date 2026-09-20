# Culinary Blog Web App

This folder contains the Next.js App Router frontend. Use the root [README](../README.md) for setup and test commands.

The Agent Bootstrap includes a category page with loading, empty, and error states.

Issue #2 adds `/admin/categories`. Sign in with an existing Admin account,
then create categories or select one to edit its name and description. The page
shows validation, permission, network, loading, empty, and save states. Its
access token stays in page memory and is cleared on sign-out or an unauthorized
save; a reload requires sign-in again. The API checks Admin permission for every
write. The page uses the existing Small Kitchen palette and does not change the
public homepage components. Category reads use `cache: "no-store"` so an Admin
edit appears on the next public request.
