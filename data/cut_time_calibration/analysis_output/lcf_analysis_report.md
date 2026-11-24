# LCF Profile Inventory and Structural Analysis

> Read-only analysis of profiles in the configured 60W and 100W folders. Each LCF section is analyzed as a separate record. No parameter semantics or array positions are inferred.

## Dataset

- Source files: **37**
- Section records: **39**
- 60W folder: **21 files**, **22 sections/records**
- 100W folder: **16 files**, **17 sections/records**

## Sections encountered

| Section | Records | Folder origin |
|---|---:|---|
| `iLASER-4000` | 22 | 60W: 21, 100W: 1 |
| `iLASER-4000_S-100W` | 17 | 60W: 1, 100W: 16 |

## Key coverage across section records

| Key | Present | Missing | Unique raw values | Multi-token records | Token lengths |
|---|---:|---:|---:|---:|---|
| `AirBlow` | 17 | 22 | 2 | 0 | — |
| `AirBlowFlag` | 17 | 22 | 2 | 17 | 8 |
| `Autorun` | 39 | 0 | 1 | 0 | — |
| `Copy` | 39 | 0 | 1 | 0 | — |
| `CustomLanguage` | 39 | 0 | 1 | 0 | — |
| `CustomPower` | 39 | 0 | 2 | 0 | — |
| `CustomPower0` | 39 | 0 | 1 | 39 | 14 |
| `CustomPower1` | 39 | 0 | 1 | 39 | 14 |
| `CustomPower2` | 39 | 0 | 1 | 39 | 14 |
| `CustomPower3` | 39 | 0 | 1 | 39 | 14 |
| `CustomPower4` | 39 | 0 | 1 | 39 | 14 |
| `CustomPowerName0` | 39 | 0 | 1 | 0 | — |
| `CustomPowerName1` | 39 | 0 | 1 | 0 | — |
| `CustomPowerName2` | 39 | 0 | 1 | 0 | — |
| `CustomPowerName3` | 39 | 0 | 1 | 0 | — |
| `CustomPowerName4` | 39 | 0 | 1 | 0 | — |
| `Cut` | 39 | 0 | 1 | 0 | — |
| `CutFlag` | 39 | 0 | 1 | 39 | 8 |
| `CutMode` | 39 | 0 | 1 | 0 | — |
| `DefaultLanguage` | 39 | 0 | 1 | 0 | — |
| `DitheringMethod` | 39 | 0 | 1 | 0 | — |
| `DualHead` | 39 | 0 | 1 | 0 | — |
| `Engrave` | 39 | 0 | 1 | 0 | — |
| `EngraveFlag` | 39 | 0 | 1 | 39 | 8 |
| `FixFQ` | 39 | 0 | 1 | 39 | 8 |
| `GrayMode` | 39 | 0 | 1 | 0 | — |
| `Halftone` | 39 | 0 | 2 | 0 | — |
| `Invert` | 39 | 0 | 1 | 0 | — |
| `JobTitle` | 39 | 0 | 1 | 0 | — |
| `JointCurves` | 39 | 0 | 2 | 0 | — |
| `LaserFlag` | 39 | 0 | 2 | 39 | 3, 5 |
| `MaterialLX` | 39 | 0 | 2 | 0 | — |
| `MaterialLX_inch` | 39 | 0 | 2 | 0 | — |
| `MaterialLength` | 39 | 0 | 1 | 0 | — |
| `MaterialLength_inch` | 39 | 0 | 1 | 0 | — |
| `MaterialRadius` | 39 | 0 | 1 | 0 | — |
| `MaterialSetup` | 39 | 0 | 1 | 0 | — |
| `MaterialSize` | 39 | 0 | 1 | 0 | — |
| `MaterialSize_inch` | 39 | 0 | 1 | 0 | — |
| `Mirror` | 39 | 0 | 1 | 0 | — |
| `Mode` | 39 | 0 | 2 | 0 | — |
| `Orientation` | 39 | 0 | 1 | 0 | — |
| `PPI` | 39 | 0 | 2 | 39 | 8 |
| `PPISTEP` | 39 | 0 | 2 | 39 | 8 |
| `PageHeight` | 39 | 0 | 1 | 0 | — |
| `PageWidth` | 39 | 0 | 1 | 0 | — |
| `Password` | 39 | 0 | 1 | 0 | — |
| `PolygonOffset` | 39 | 0 | 1 | 39 | 8 |
| `Power` | 39 | 0 | 28 | 39 | 8 |
| `PowerHighLimit` | 39 | 0 | 1 | 0 | — |
| `PowerLowLimit` | 39 | 0 | 1 | 0 | — |
| `PowerScale` | 39 | 0 | 1 | 39 | 14 |
| `PulseCount` | 39 | 0 | 1 | 0 | — |
| `PulseDisableTime` | 39 | 0 | 2 | 0 | — |
| `PulseEnableTime` | 39 | 0 | 1 | 0 | — |
| `PulseMode` | 39 | 0 | 2 | 0 | — |
| `Quantity` | 39 | 0 | 1 | 0 | — |
| `RasterDirection` | 39 | 0 | 2 | 0 | — |
| `RasterEnd` | 39 | 0 | 2 | 0 | — |
| `RasterShiftL2R` | 39 | 0 | 1 | 39 | 6 |
| `RasterShiftR2L` | 39 | 0 | 1 | 39 | 6 |
| `RelativePoint` | 39 | 0 | 1 | 0 | — |
| `Resolution` | 39 | 0 | 1 | 0 | — |
| `RotaryAutoShift` | 39 | 0 | 1 | 0 | — |
| `RotaryRDPI` | 39 | 0 | 1 | 0 | — |
| `RotaryRResolution` | 39 | 0 | 1 | 0 | — |
| `RotaryRStep` | 39 | 0 | 1 | 0 | — |
| `RotaryXResolution` | 39 | 0 | 1 | 0 | — |
| `RotateMode` | 39 | 0 | 1 | 0 | — |
| `ScaleXaxis` | 39 | 0 | 1 | 0 | — |
| `ScaleYaxis` | 39 | 0 | 1 | 0 | — |
| `ScanlineOrder` | 39 | 0 | 2 | 0 | — |
| `SelectedPowerScale` | 39 | 0 | 1 | 0 | — |
| `Sequence` | 39 | 0 | 1 | 0 | — |
| `ShiftResolution` | 39 | 0 | 1 | 0 | — |
| `ShowTime` | 39 | 0 | 1 | 0 | — |
| `Speed` | 39 | 0 | 38 | 39 | 8 |
| `StampOffset` | 39 | 0 | 1 | 0 | — |
| `StayComplete` | 39 | 0 | 1 | 0 | — |
| `TemporaryReferencePoint` | 39 | 0 | 1 | 0 | — |
| `Unit` | 39 | 0 | 1 | 0 | — |
| `VectorOptimization` | 39 | 0 | 2 | 0 | — |
| `ZaxisMode` | 17 | 22 | 1 | 0 | — |
| `ZaxisOffset` | 17 | 22 | 1 | 17 | 8 |
| `ZaxisPitch` | 17 | 22 | 1 | 0 | — |

## Raw-value variation by folder origin

### 60W

| Key | Records containing key | Unique values |
|---|---:|---:|
| `CustomPower` | 22 | 2 |
| `JointCurves` | 22 | 2 |
| `LaserFlag` | 22 | 2 |
| `MaterialLX` | 22 | 2 |
| `MaterialLX_inch` | 22 | 2 |
| `Mode` | 22 | 2 |
| `PPI` | 22 | 2 |
| `PPISTEP` | 22 | 2 |
| `Power` | 22 | 15 |
| `RasterDirection` | 22 | 2 |
| `RasterEnd` | 22 | 2 |
| `ScanlineOrder` | 22 | 2 |
| `Speed` | 22 | 21 |
| `VectorOptimization` | 22 | 2 |

### 100W

| Key | Records containing key | Unique values |
|---|---:|---:|
| `AirBlow` | 16 | 2 |
| `AirBlowFlag` | 16 | 2 |
| `CustomPower` | 17 | 2 |
| `Halftone` | 17 | 2 |
| `JointCurves` | 17 | 2 |
| `LaserFlag` | 17 | 2 |
| `MaterialLX` | 17 | 2 |
| `MaterialLX_inch` | 17 | 2 |
| `Mode` | 17 | 2 |
| `PPI` | 17 | 2 |
| `PPISTEP` | 17 | 2 |
| `Power` | 17 | 13 |
| `PulseDisableTime` | 17 | 2 |
| `PulseMode` | 17 | 2 |
| `RasterDirection` | 17 | 2 |
| `RasterEnd` | 17 | 2 |
| `ScanlineOrder` | 17 | 2 |
| `Speed` | 17 | 17 |
| `VectorOptimization` | 17 | 2 |

## Exact section-content duplicates

Identical section dictionaries are grouped regardless of filename or folder origin.

No identical section-content groups detected.

## Array/token-length observations

Lengths are descriptive only; token positions are not interpreted.

### `AirBlowFlag`

- Multi-token records: **17**
- Length distribution: 8: 17

### `CustomPower0`

- Multi-token records: **39**
- Length distribution: 14: 39

### `CustomPower1`

- Multi-token records: **39**
- Length distribution: 14: 39

### `CustomPower2`

- Multi-token records: **39**
- Length distribution: 14: 39

### `CustomPower3`

- Multi-token records: **39**
- Length distribution: 14: 39

### `CustomPower4`

- Multi-token records: **39**
- Length distribution: 14: 39

### `CutFlag`

- Multi-token records: **39**
- Length distribution: 8: 39

### `EngraveFlag`

- Multi-token records: **39**
- Length distribution: 8: 39

### `FixFQ`

- Multi-token records: **39**
- Length distribution: 8: 39

### `LaserFlag`

- Multi-token records: **39**
- Length distribution: 3: 22, 5: 17

### `PPI`

- Multi-token records: **39**
- Length distribution: 8: 39

### `PPISTEP`

- Multi-token records: **39**
- Length distribution: 8: 39

### `PolygonOffset`

- Multi-token records: **39**
- Length distribution: 8: 39

### `Power`

- Multi-token records: **39**
- Length distribution: 8: 39

### `PowerScale`

- Multi-token records: **39**
- Length distribution: 14: 39

### `RasterShiftL2R`

- Multi-token records: **39**
- Length distribution: 6: 39

### `RasterShiftR2L`

- Multi-token records: **39**
- Length distribution: 6: 39

### `Speed`

- Multi-token records: **39**
- Length distribution: 8: 39

### `ZaxisOffset`

- Multi-token records: **17**
- Length distribution: 8: 17

## Data preservation

- JSON retains the complete parsed key/value dictionary for each section record.
- CSV contains one row per section record, with raw values.
- Folder origin and actual section name are retained separately.
- No array channel mapping or parameter semantics are inferred.
