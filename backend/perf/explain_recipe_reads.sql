-- Run against PostgreSQL after seeding representative data. Replace the slug
-- and query with known published rows before reviewing the execution plan.
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, title, slug, category_id, created_at
FROM recipes
WHERE is_deleted = false AND status = 1
ORDER BY created_at DESC, id DESC LIMIT 12;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, title, slug, category_id, created_at
FROM recipes
WHERE is_deleted = false AND status = 1 AND category_id = (
  SELECT id FROM categories LIMIT 1
)
ORDER BY created_at DESC, id DESC LIMIT 12;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id, title, slug
FROM recipes
WHERE is_deleted = false AND status = 1
  AND search_vector @@ to_tsquery('simple', 'pho:*')
ORDER BY ts_rank(search_vector, to_tsquery('simple', 'pho:*')) DESC,
  created_at DESC, id DESC LIMIT 12;

EXPLAIN (ANALYZE, BUFFERS)
SELECT r.id, r.title, r.slug, c.name AS category_name, u.full_name AS author_name
FROM recipes AS r
JOIN categories AS c ON c.id = r.category_id
JOIN users AS u ON u.id = r.author_id
WHERE r.slug = (
  SELECT slug FROM recipes WHERE is_deleted = false AND status = 1 LIMIT 1
) AND r.is_deleted = false;
