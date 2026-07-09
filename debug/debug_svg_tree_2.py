import xml.etree.ElementTree as ET

tree = ET.parse("Cartouche_C.text.svg")
root = tree.getroot()

def strip(tag):
    return tag.split("}", 1)[1] if "}" in tag else tag

XLINK = "{http://www.w3.org/1999/xlink}href"

count = 0

for symbol in root.iter():

    if strip(symbol.tag) != "symbol":
        continue

    print()
    print(symbol.attrib.get("id"))

    for child in symbol:
        print(
            "   ",
            strip(child.tag),
            child.attrib.get("transform")
        )

    break
