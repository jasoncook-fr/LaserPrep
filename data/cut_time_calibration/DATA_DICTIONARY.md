# Data dictionary

## Controlled tests
The canonical controlled-test CSV currently uses the following fields:

| Field | Meaning |
|---|---|
| record_id | Unique calibration observation ID (CAL-####). |
| source | Source workbook or origin. |
| test_group | Experimental series/context. |
| machine | Machine designation (e.g. 60W, 100W). |
| optimization | Recorded optimization state or experimental condition; legacy combined labels may remain pending clarification. |
| measurement_type | Type of test, e.g. mixed line/spline cut or filled engraving. |
| geometry | Text description of geometry/conditions. |
| actual_time_seconds | Observed duration in seconds. |
| measurement_units | Units for time. |
| derived_rate | Optional derived rate; must not replace the actual observation. |
| notes | Provenance, caveats and context. |

## Production jobs

| Field | Meaning |
|---|---|
| job_id | Unique production observation ID (JOB-####). |
| date | Date recorded (ISO format preferred). |
| svg_filename | Source SVG filename. |
| machine | Machine designation. |
| actual_time_seconds | Actual elapsed job time in seconds. |
| notes | Context/caveats. |
| path_count | Total path count if available. |
| blue_cut_paths | Blue cutting paths count, if available. |
| green_engrave_paths | Green vector engraving paths count, if available. |
| red_engrave_paths | Red vector engraving paths count, if available. |
| black_fill_paths | Black filled paths count, if available. |
| optimisation | Legacy or combined description; prefer independent fields in future schema revisions. |
| profile_filename | LCF profile used. |
| profile_adjusted | Whether profile was adjusted. |
| speed_factor | Profile adjustment factor, if known. |
| material | Material and thickness. |
| blue_cut_straight_mm | Straight blue cutting length (mm). |
| blue_cut_curves_mm | Curved blue cutting length (mm). |
| green_vector_mm | Green vector engraving length (mm). |
| red_vector_mm | Red vector engraving length (mm). |
| black_fill_area_mm2 | Black fill area (mm²). |
| repeat_number | Repeat/run number when applicable. |
| operator_notes | Additional operator context and quality notes. |

## Future schema improvements
For production jobs, split optimization into two explicit Boolean/enum fields: `optim_vectors` and `jct_curves`. Also consider fields for cut/engrave profile speed and power by color, orientation, job start/stop overhead, material batch, and quality status. Do not retrofit missing values without evidence.
