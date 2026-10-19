# UI design tokens

The frontend uses Tailwind CSS 4 for the utility layer and CSS Modules for
component-specific layout. The shared semantic tokens live in
`frontend/src/styles/tokens.css` and are imported by `app/globals.css`.

## Shared tokens

- **Color:** `--paper`, `--cream`, `--ink`, `--moss`, `--clay`, `--saffron`,
  `--muted`, and `--line`.
- **Focus:** `--focus-ring` and `--focus-offset` provide one visible keyboard
  focus treatment across the public blog UI.
- **Spacing:** `--space-1` through `--space-8` use a four-pixel base scale.
- **Shape and elevation:** `--radius-sm`, `--radius-md`, `--radius-lg`, and
  `--shadow-panel` cover repeated panel treatments.
- **Typography:** `--font-body` and `--font-display` keep body and editorial
  headings consistent.

New shared UI should use these semantic variables. A CSS Module may add a
component-only token when the value is not reused elsewhere. Do not add a
second UI framework or duplicate the token definitions in individual pages.

The Admin workspace retains its TailAdmin-inspired blue navigation tokens in
its page module because that surface is intentionally separate from the
public food blog theme. Its shared focus behavior still comes from the global
`:focus-visible` rule.
