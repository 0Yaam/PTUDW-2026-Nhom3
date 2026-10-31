# Recipe image management

FR-RCP-008 provides image upload, primary selection, and deletion. The recipe
detail page shows those controls only to the authenticated owner or an Admin;
the API checks permission again for every write. After creating a Draft, the
success message links to its detail page so its owner can add photos. No sample
recipe images are inserted by this feature.

| Action | Endpoint | Result |
|---|---|---|
| Upload | `POST /api/v1/recipes/{id}/images` | `201`, new image; first image is primary |
| Set primary | `PATCH /api/v1/recipes/{id}/images/{imageId}` with `{"isPrimary":true}` | `200` |
| Delete | `DELETE /api/v1/recipes/{id}/images/{imageId}` | `204`; next image becomes primary if needed |
| Replace file | `POST /api/v1/recipes/{id}/images/{imageId}/replace` | `201`, new image and `Location` |

Upload and replacement use `multipart/form-data` with a `file` field. The API
accepts JPEG, PNG, WebP, or AVIF up to 5 MiB and verifies the file signature.
Invalid files return RFC 7807 `400`; storage failure returns `503`; missing
authentication, another owner's recipe, or an unknown recipe/image returns
`401`, `403`, or `404` respectively.

Replacement is an explicit extension to FR-RCP-008. It creates a new image ID
while preserving the old image's position, primary flag, and alt text. The old
original and WebP variants are queued for cleanup, and a resize job is queued
for the new original in the same database transaction. Different IDs give the
old and new variants different object keys, so delayed cleanup cannot delete
the replacement. Until resize finishes, the detail page uses `originalUrl`.
Image writes invalidate the recipe cache.

The owner/Admin UI uses CSS Modules local to the recipe components. Visitors
retain the existing read-only gallery and placeholder. After any image action,
the detail is fetched again so the gallery reflects the database state.
