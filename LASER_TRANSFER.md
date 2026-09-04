# Laser Transfer

## Status

**Proof of concept successfully demonstrated.**

LaserPrep can generate an LTT/PRN file containing vector geometry and transmit it directly to the laser cutter over TCP.

The generated geometry has been physically verified on the machine.

## Verified Protocol Elements

The observed PRN stream contains:

- LTT job header
- PSPA records
- PDPR coordinate records
- PR movement records
- PU pen-up records
- BYE termination

Coordinates are encoded as signed 32-bit big-endian integers.

## Transfer

Create an SVG file in Inkscape and export/save a Windows-generated PRN file from the same geometry. The Windows-generated PRN is used as a reference for identifying the commands and protocol structure required by the laser cutter.

For example:

```bash
python3 svg_to_prn.py test-geometry-WIN.prn test-geometry.svg test-geometry-GEN2.prn
```

The generated PRN can then be sent directly to the laser cutter over TCP port `9100`.

Example for the 60W laser:

```bash
nc 192.168.18.11 9100 < test-geometry-GEN2.prn
```

## Geometry

The current proof of concept has successfully generated:

- Horizontal lines
- Vertical lines
- Rectangles
- Multiple independent paths
- Arbitrary test geometry generated from SVG

The generated geometry has been physically verified on the laser cutter.

## Important Workflow Requirement

The Windows/Inkscape workflow requires vector strokes to be **0.01 mm** for the geometry to be considered valid by the machine workflow.

## Current Limitation

The LTT protocol implementation is currently being reconstructed from observed Windows-generated PRN files.

The next stage is to integrate PRN generation with LaserPrep's existing geometry model rather than relying on standalone test files.

## TODO

### Laser-Cut Profiles

Analyze the files in the `laser-cut-profiles` folder. These files use the `.lcf` extension and appear to contain the parameters required for cutting and engraving, including:

- Speed
- Power
- Material-specific settings
- Other machine parameters

Determine the `.lcf` file format and how its parameters map to the commands/settings required by the laser cutter.

### Reference PRN

Continue analyzing:

```text
test-geometry-WIN.prn
```

Use Windows-generated PRN files as references for reconstructing the remaining LTT protocol elements.
