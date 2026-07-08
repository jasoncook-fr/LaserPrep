#!/usr/bin/env python3

import re
import sys
import xml.etree.ElementTree as ET

SVG = "{http://www.w3.org/2000/svg}"


number = re.compile(r"-?\d+(?:\.\d+)?")


def command_count(d):

    counts = {}

    for c in "MLCQAZHV":
        n = d.count(c)
        if n:
            counts[c] = n

    return counts


def extract_numbers(d):

    return [float(x) for x in number.findall(d)]


def main(filename):

    tree = ET.parse(filename)
    root = tree.getroot()

    paths = root.findall(f".//{SVG}path")

    print("=" * 70)
    print(filename)
    print("=" * 70)

    print()
    print(f"Paths : {len(paths)}")

    xmin = float("inf")
    ymin = float("inf")
    xmax = float("-inf")
    ymax = float("-inf")

    empty = 0

    total_commands = {}

    for i, path in enumerate(paths):

        d = path.attrib.get("d", "")

        if not d.strip():
            empty += 1
            continue

        cmds = command_count(d)

        for k, v in cmds.items():
            total_commands[k] = total_commands.get(k, 0) + v

        nums = extract_numbers(d)

        xs = nums[0::2]
        ys = nums[1::2]

        if xs:
            xmin = min(xmin, min(xs))
            xmax = max(xmax, max(xs))

        if ys:
            ymin = min(ymin, min(ys))
            ymax = max(ymax, max(ys))

    print()
    print("Commands")

    for k in sorted(total_commands):
        print(f"{k} : {total_commands[k]}")

    print()

    print(f"Empty paths : {empty}")

    print()

    print("Global coordinate bounds")

    print(f"Left   : {xmin:.3f}")
    print(f"Top    : {ymin:.3f}")
    print(f"Right  : {xmax:.3f}")
    print(f"Bottom : {ymax:.3f}")



if __name__ == "__main__":

    if len(sys.argv) != 2:
        print("Usage")
        print("python inspect_svg.py file.svg")
        sys.exit()

    main(sys.argv[1])
