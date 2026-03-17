# Notion Feed Overview Design

## Goal

Make the Notion shortlist database usable as a real review feed for scrolling and analyzing jobs while keeping Supabase as the canonical source of truth.

## Constraints

- Keep Supabase canonical.
- Keep Notion focused on review, not raw archival storage.
- Preserve manual workflow properties: `Priority`, `Review Status`, `Application Status`, and `Notes`.
- Preserve manual page-level notes during sync.
- Backfill existing synced pages on the next sync.

## Chosen Approach

Use a hybrid Notion model:

- Compact scan fields live in database properties.
- Full job detail lives in the page body.
- The sync manages a deterministic "synced" section in the page body.
- A `Reviewer Notes` section is preserved for manual edits.

## Database Properties

Existing properties remain. Add:

- `Description Snippet`
- `Location Raw`
- `Employment Type`
- `Seniority`
- `Posted At`

Property mapping changes:

- `Job URL` should map to `source_job_url`, not `normalized_job_url`.
- `Posted Text` remains the human-readable relative posting string.
- `Description Snippet` is the first 450 characters of normalized description text.

Do not add:

- `Country`
- `First Seen At`
- Full description as a database property

## Page Body Structure

Each synced page should contain:

1. `Synced Overview`
2. `Description`
3. `Sync Metadata`
4. `Reviewer Notes`

Rules:

- The pipeline owns the first three sections.
- `Reviewer Notes` is manual and preserved on updates.
- On create, the page gets the full structure.
- On update, the synced sections are regenerated and `Reviewer Notes` is preserved.

## Sync Behavior

- Sync still keys pages by `Canonical Job Key`.
- Existing pages should be updated on the next sync if managed properties or synced content differ.
- Idempotency should consider both managed properties and synced page content.
- Long descriptions should only live in the page body; the property layer gets a capped snippet.

## Testing

Add or update tests for:

- snippet generation
- page content rendering
- create/update/skip behavior when only body content changes
- preservation of `Reviewer Notes`
- expanded schema requirements
- runtime checksum behavior including synced content
