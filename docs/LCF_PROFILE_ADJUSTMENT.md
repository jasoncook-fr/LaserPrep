# LCF Profile Adjustment Utility

This utility creates a separate set of adjusted LCF files. It does not modify the source profiles.

## Default adjustment

- Speed values are multiplied by **0.90** (a 10% reduction).
- Power, PPI, offsets, focus and all other fields are preserved.
- All eight speed slots are adjusted in every `Speed=` entry, including multi-section files.
- Raw speed values are rounded to the nearest integer.
- A CSV audit records the old and new value for each channel slot.
- A JSON summary records the factor and file count.

This is an initial blanket adjustment based on workshop experience, not a validated machine calibration. Review the resulting profiles before using them operationally.

## Run

```bash
python profile_adjustment.py /path/to/original-profiles /path/to/adjusted-profiles
```

Use another factor if appropriate:

```bash
python profile_adjustment.py /path/to/original-profiles /path/to/adjusted-profiles --speed-factor 0.85
```

The output preserves the source directory structure and includes:

- adjusted `.lcf` files
- `speed_adjustment_audit.csv`
- `adjustment_summary.json`

Never use the output directory inside the source directory. Keep the original profiles archived and read-only.
