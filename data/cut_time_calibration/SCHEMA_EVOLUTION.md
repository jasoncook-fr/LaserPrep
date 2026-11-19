# Schema and evolution

The CSV schemas are documented in `DATA_DICTIONARY.md`. Each row represents one observed job or one experimental observation. IDs are stable and unique.

When changing schemas:
1. Prefer additive changes.
2. Document meaning, units, allowed values and null behavior.
3. Update normalization scripts and tests.
4. Preserve raw-source references.
5. Do not reuse IDs or silently change interpretation of existing fields.

Production dataset currently includes a legacy `optimisation` field. Future records should capture Optim. Vectors and JcT Courbes as separate fields. Existing records must not be retroactively inferred unless source evidence supports the change.
