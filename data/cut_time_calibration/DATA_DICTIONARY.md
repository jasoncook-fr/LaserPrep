# Data Dictionary

## Production jobs (`production_jobs_master.csv`)

- `job_id`: stable ID (`JOB-####`).
- `date`: date the job was measured, where known.
- `svg_filename`: source SVG filename.
- `machine`: 60W or 100W.
- `actual_time_seconds`: observed runtime in seconds.
- `notes`: job-specific notes.
- `path_count`, `blue_cut_paths`, `green_engrave_paths`, `red_engrave_paths`, `black_fill_paths`: existing geometry/path counts, if captured.
- `optimisation`: legacy combined note; future records should separate the two optimization toggles.
- `profile_filename`: machine profile used, if known.
- `profile_adjusted`: whether a modified profile was used, if known.
- `speed_factor`: profile adjustment factor, if known.
- `material`: material and thickness, if known.
- `blue_cut_straight_mm`, `blue_cut_curves_mm`, `green_vector_mm`, `red_vector_mm`: measured geometry lengths in mm.
- `black_fill_area_mm2`: filled area in square mm.
- `repeat_number`: repeat/replicate identifier, if relevant.
- `operator_notes`: additional context.

Legacy fields are retained. Where possible, future rows should capture Optim. Vectors and JcT Courbes as separate explicit fields; the existing combined `optimisation` field is not a substitute for those fields.

## Controlled tests (`controlled_tests_master.csv`)

- `record_id`: stable ID (`CAL-####`).
- `source`: original source filename or reference.
- `test_group`: experiment grouping.
- `machine`: 60W or 100W.
- `optimization`: setting or experimental condition as transcribed; currently often JcT ON/OFF or scan direction. This column is historical and not a fully normalized pair of machine toggles.
- `measurement_type`: what was measured.
- `geometry`: shape, dimensions, distance or line/spline composition as described in source.
- `actual_time_seconds`: measured duration in seconds.
- `measurement_units`: time unit, generally seconds.
- `derived_rate`: optional calculated rate; blank where not recalculated.
- `notes`: provenance, interpretation limitations and caveats.

The controlled CSV is a transcription/normalization of the colleague's measurements. Do not interpret unknown details as known facts.