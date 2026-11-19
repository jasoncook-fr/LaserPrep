# Schema Evolution

The CSV schema is evolving as the experiment grows.

## Rules

- Prefer additive fields to renaming/removing existing fields.
- Preserve legacy columns so earlier observations remain readable.
- Document units and definitions in the data dictionary.
- Do not change a field's meaning without versioning or migration notes.
- Normalize new experimental dimensions only when the definitions are clear.
- Consider a separate schema version/quality status field in future revisions.

## Planned improvements

1. Split Optim. Vectors and JcT Courbes into independent columns for production records.
2. Explicitly record laser speed setting (percentage) for controlled tests.
3. Record profile power/speed values and profile revision where relevant.
4. Clarify fill engraving direction, scan strategy, and other fill settings.
5. Add a data-quality flag and timing-method field.
6. Archive source spreadsheet and raw files with the normalized data.

Changes should be reviewed against existing records before applying a migration.