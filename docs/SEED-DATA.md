# Real recipe dataset

The course requires real content: at least 10 categories and 50 recipes, each
with complete cooking steps, ingredients and an illustration, and no random test
data. `backend/seed_data` holds that dataset and `culinary_blog_api.seed` loads it.

| Item | Content |
|---|---|
| Categories | 11 Vietnamese categories (`mon-nuoc`, `mon-man-an-com`, `mon-xao`, `canh-va-sup`, `goi-va-mon-cuon`, `banh-va-an-vat`, `hai-san`, `mon-chay`, `mon-an-sang`, `che-va-trang-mieng`, `do-uong`) |
| Recipes | 55 published Vietnamese dishes, 5 per category |
| Per recipe | description, prep/cook time, servings, difficulty, nutrition, 5–11 ingredients with quantity and unit, 4–6 numbered cooking steps with durations, one primary photo |
| Photos | `seed_data/images/<slug>.jpg`, at most 1200 px; Creative Commons (CC0 / CC BY / CC BY-SA) photos from Wikimedia Commons, Flickr, and one CC0 Rawpixel source found through Openverse |
| Credits | `seed_data/images/credits.json` lists file title, available author, license and source page for every photo |

Recipe text (ingredients, quantities and steps) was written by the team for this
project; it is not copied from a single website.

## What `seed` does

The API container runs `alembic upgrade head && seed` on start; run it manually
with `docker compose exec api seed`. Each run is idempotent:

1. Removes generated and test-only data: the old Lab 2 author
   (`lab2-author@example.local`) with its 100 generated recipes, accounts created
   by end-to-end tests (`e2e-*@example.com`) with their recipes, the 20 old English
   starter categories and `E2E …` categories when no recipe uses them, and
   ingredients that no recipe references. Photos of removed recipes are queued in
   `file_deletion_jobs`.
2. Creates missing categories (Admin edits to existing categories are kept) and
   creates or updates the 55 recipes owned by the editorial account
   `bep@culinary-blog.local` (random password, not used for sign-in). Ingredients
   and steps are replaced from the dataset; a recipe with the same slug owned by a
   real user is never taken over.
3. Uploads each recipe photo to MinIO once and queues the resize job, so the image
   worker creates the medium and thumbnail variants.

Seed deliberately does not overwrite a recipe image that already exists. To
replace one of the curated photos, use the recipe image replacement action in
the application; copying another `.jpg` over the seed file and rerunning `seed`
only affects a fresh database.

Real users' recipes and accounts are not touched. The Playwright suite runs the
seed again in its global teardown, so test accounts and categories do not remain.
