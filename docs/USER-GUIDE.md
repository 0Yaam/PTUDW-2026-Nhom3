# User Guide

Short walkthrough of the public flows in Small Kitchen: register, sign in,
create a recipe, publish it, and search the published list.

The site runs on `http://localhost:3001`, the API on `http://localhost:8000`.
Start both with `docker compose up` or `start-all.ps1`. Every page is bilingual:
the **VI / EN** switch in the header stores your choice in the `NEXT_LOCALE`
cookie, so it survives a reload.

## 1. Register

1. Open `http://localhost:3001` and go to the **Account** section (header link, or
   scroll to the bottom of the home page).
2. Keep the **Register** tab selected and fill in:
   - **Full name** — up to 150 characters.
   - **Username** — 3 to 50 characters, letters, digits, and `_` only.
   - **Email** — must be a valid address, and unique.
   - **Password** — at least 8 characters.
3. Press **Register**. On success the panel greets you by name and shows your
   roles; the form clears and you are signed in already.

If something is wrong, the message under the form explains it (for example a
duplicate email). The message area is announced to screen readers, and the form
is linked to it with `aria-describedby`, so the reason is read out without
hunting for it.

## 2. Sign in and sign out

1. In the **Account** section pick the **Login** tab.
2. Enter your email and password, then press **Login**.
3. The session (access token, refresh token, expiry) is kept in the browser.
   An expired access token is refreshed automatically on the next request; if
   the refresh also fails, the page asks you to sign in again.
4. **Sign out** appears in the same panel once you are signed in, and clears
   the stored session.

## 3. Create a recipe

Signing in is required: without a session, `/recipes/new` shows a
*Sign in to continue* card instead of the form.

1. Go to **Create recipe** in the header, or `http://localhost:3001/recipes/new`.
2. Fill in the four sections:
   - **01 Basics** — title (5 to 200 characters), description (required, up to
     2000 characters), and a category from the list.
   - **02 Time and servings** — prep time (at least 1 minute), cook time (0 or
     more), servings (at least 1), and a difficulty from Easy to Hard.
   - **03 Instructions** — free text for now. Structured cooking steps are a
     separate issue and are added through the API.
   - **04 Nutrition** — optional, collapsed by default. Values cannot be
     negative.
3. The sidebar previews the title, category, total time, servings, and
   difficulty while you type.
4. Press **Save draft**. The green banner confirms the title and slug.
   **Create another** clears the form.

The recipe is saved as a **draft**: only you can see it. If a field is
rejected, the inline message appears under that field and focus jumps to the
first rejected field, so keyboard users do not have to search for it.

## 4. Publish a recipe

Publishing is currently an API action — there is no button in the UI yet
(tracked separately from this guide).

```bash
# Replace the token and recipe id with your own.
curl -X PATCH http://localhost:8000/api/v1/recipes/<recipe-id>/publish \
  -H "Authorization: Bearer <access-token>"
```

Only the recipe owner may publish it. Related actions use the same shape:
`/unpublish` returns a recipe to draft, and `/archive` hides it from the public
list.

Once published the recipe:

- appears in the public list at `/recipes` and on its category page,
- is reachable at `/recipes/<slug>` without signing in,
- is listed in `/sitemap.xml` and carries its own title, description, canonical
  URL, and `Recipe` structured data.

Drafts and archived recipes stay out of the sitemap and out of the public list.

## 5. Search and browse

1. Open **Recipes** in the header, or `http://localhost:3001/recipes`.
2. Use the filter bar:
   - **Search** — matches title and description, 2 characters minimum.
   - **Category**, **Difficulty**, **Max cook time**, **Min servings**.
   - **Sort** — newest, oldest, title, or cook time, ascending or descending.
3. Press **Apply** to run the search, **Reset** to clear every filter.
4. Results are paginated 12 per page; **Previous** and **Next** move between
   pages, and the page counter shows where you are.
5. Click a card, or its **View detail** link, to open the recipe.

Three states are distinguishable while you browse: a skeleton placeholder with
a *Loading* announcement, an empty-result panel explaining that no recipe
matches, and an error panel with a **Retry** button when the API cannot be
reached.

Browsing by category instead: the home page **Categories** grid links to
`/categories/<slug>`, which lists the published recipes in that category, or
explains that the category is still empty.

## Keyboard and screen reader notes

- The first <kbd>Tab</kbd> on any page reveals **Skip to content**, which jumps
  past the navigation to the main region.
- Every interactive element is reachable with <kbd>Tab</kbd> and shows a visible
  focus ring. Nothing depends on hovering or on a mouse.
- The mobile menu is a native `<details>` element: <kbd>Enter</kbd> or
  <kbd>Space</kbd> opens and closes it, and it closes itself on navigation.
- Form problems are reported in text next to the field, never by colour alone.
- Loading, empty, and error states are announced, so they are not silent for
  screen reader users.

See [FRONTEND-QA.md](FRONTEND-QA.md) for the accessibility, SEO, and
performance checks behind these notes.
