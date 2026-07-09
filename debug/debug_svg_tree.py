from pathlib import Path
import xml.etree.ElementTree as ET

SVG = Path("Cartouche_A.text.svg")

tree = ET.parse(SVG)
root = tree.getroot()


def strip(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag


def dump(node, depth=0):

    indent = "    " * depth

    line = indent + strip(node.tag)

    if "id" in node.attrib:
        line += f" id='{node.attrib['id']}'"

    if "transform" in node.attrib:
        t = node.attrib["transform"]
        if len(t) > 70:
            t = t[:70] + "..."
        line += f" transform='{t}'"

    if strip(node.tag) == "path":
        d = node.attrib.get("d", "")
        line += f"  dlen={len(d)}"

    print(line)

    for child in node:
        dump(child, depth + 1)


print()
print("=" * 60)
print("SVG DOCUMENT TREE")
print("=" * 60)
print()

dump(root)
