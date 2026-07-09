from pathlib import Path
import xml.etree.ElementTree as ET

SVG = Path("Cartouche_A.text.svg")
OUTPUT = Path("output")
OUTPUT.mkdir(exist_ok=True)

tree = ET.parse(SVG)
root = tree.getroot()


def strip(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


# -------------------------------------------------------
# Export the first N matching paths
# -------------------------------------------------------

START = 1
COUNT = 1000

svg = ET.Element(
    "svg",
    xmlns="http://www.w3.org/2000/svg",
    width="500mm",
    height="500mm",
    viewBox="0 0 2000 2000",
)

candidate = 0
exported = 0

for node in root.iter():

    if strip(node.tag) != "path":
        continue

    # ---------- choose what to export ----------

    # OPTION A
    # Export only paths WITHOUT a transform.
    if node.attrib.get("transform"):
        continue

    # OPTION B
    # Uncomment these instead if you want only long Bézier paths.
    #
    # d = node.attrib.get("d", "")
    #
    # if "C" not in d:
    #     continue
    #
    # if len(d) < 300:
    #     continue

    candidate += 1

    if candidate < START:
        continue

    if exported >= COUNT:
        break

    exported += 1

    print(f"Exporting path {candidate}")

    attrs = {
        "d": node.attrib.get("d", ""),
        "stroke": "red",
        "fill": "none",
        "stroke-width": "0.5",
    }

    if "transform" in node.attrib:
        attrs["transform"] = node.attrib["transform"]

    ET.SubElement(svg, "path", attrs)

ET.ElementTree(svg).write(
    OUTPUT / "paths.svg",
    encoding="utf-8",
    xml_declaration=True,
)

print()
print(f"Exported {exported} paths.")
print("Written output/paths.svg")
