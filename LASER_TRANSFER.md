# Laser Transfer

## Status

Proof of concept successfully demonstrated.

LaserPrep can generate an LTT/PRN file containing vector geometry
and transmit it directly to the laser cutter over TCP.

The generated geometry has been physically verified on the machine.

## Verified protocol elements

The observed PRN stream contains:

- LTT job header
- PSPA records
- PDPR coordinate records
- PR movement records
- PU pen-up records
- BYE termination

Coordinates are encoded as signed 32-bit big-endian integers.

## Transfer

The laser cutter accepts the generated PRN over TCP port 9100.

Example:

    nc -v <laser-ip> 9100 < job.prn

## Geometry

The current proof-of-concept has successfully generated:

- horizontal lines
- vertical lines
- rectangles
- multiple independent paths
- arbitrary test geometry generated from SVG

The generated geometry has been physically verified on the laser cutter.

## Important workflow requirement

The Windows/Inkscape workflow requires vector strokes to be
0.01 mm in order for the geometry to be considered valid by
the machine workflow.

## Current limitation

The LTT protocol implementation is currently being reconstructed
from observed Windows-generated PRN files.

The next stage is to integrate PRN generation with LaserPrep's
existing geometry model rather than relying on standalone test
files.
