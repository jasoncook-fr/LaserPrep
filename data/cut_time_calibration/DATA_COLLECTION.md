# Data Collection Protocol

## Production jobs

Whenever feasible, capture:

- original SVG and filename;
- actual measured machine runtime (seconds);
- machine (60W or 100W);
- material and thickness;
- exact LCF profile filename and whether adjusted;
- profile adjustment factor;
- Optim. Vectors: ON/OFF;
- JcT Courbes: ON/OFF;
- geometry metrics from LaserPrep;
- operator notes, unusual interruptions or timing method.

Do not estimate missing metadata after the fact without clearly marking it as an inference. Record the source of each time measurement.

## Controlled tests

Capture the intended variable and all settings that are held constant. Repeat measurements where feasible. Store raw measurements, not only derived rates. Identify replicate runs and avoid mistaking copies or derived values for independent observations.

## Timing convention

Clarify whether time means machine execution time, timer duration, or another definition. Use one definition consistently and record exceptions.

## Material and profile

Material labels should include type and thickness. Profiles should be identified by filename/version and adjustment factor when available.

## Quality flags

Use notes or a future explicit quality field to distinguish verified, provisional, incomplete and suspect observations. Do not delete questionable data without preserving its provenance.