from pathlib import Path
import xml.etree.ElementTree as ET
from collections import defaultdict

SVG = Path("Cartouche_A.text.svg")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

tree = ET.parse(SVG)
root = tree.getroot()


def strip(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


# --------------------------------------------------------
# Collect paths by transform
# --------------------------------------------------------

groups = defaultdict(list)

for node in root.iter():

    if strip(node.tag) != "path":
        continue

    transform = node.attrib.get("transform", "")

    groups[transform].append(node)


print()
print("=" * 60)
print("TRANSFORM GROUPS")
print("=" * 60)

print(f"Found {len(groups)} transform groups\n")


for i, (transform, paths) in enumerate(groups.items(), start=1):

    print(f"{i:03d} : {len(paths):3d} paths")

    print(f"      {transform}")

    # ----------------------------------------------------
    # Export this transform group
    # ----------------------------------------------------

    svg = ET.Element(
        "svg",
        xmlns="http://www.w3.org/2000/svg",
        width="400mm",
        height="400mm",
        viewBox="0 0 2000 2000",
    )

    for p in paths:

        ET.SubElement(
            svg,
            "path",
            {
                "d": p.attrib.get("d", ""),
                "transform": transform,
                "stroke": "red",
                "fill": "none",
                "stroke-width": "0.5",
            },
        )

    filename = OUTPUT / f"group_{i:03d}.svg"

    ET.ElementTree(svg).write(
        filename,
        encoding="utf-8",
        xml_declaration=True,
    )

print()
print("Finished.")
print(f"Generated {len(groups)} SVG files.")
