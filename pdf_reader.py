import fitz

from drawing import *
from vector_path import VectorPath

PT_TO_MM = 25.4 / 72.0

def make_point(pdf_point):
    return Point(pdf_point.x * PT_TO_MM, pdf_point.y * PT_TO_MM)

def read_pdf(filename):
    doc = fitz.open(filename)
    page = doc[0]

    drawing = Drawing(
        name=filename.stem,
        width=page.rect.width * PT_TO_MM,
        height=page.rect.height * PT_TO_MM,
    )

    unsupported = {}
    drawings = page.get_drawings()
    import_order = 0

    for d in drawings:
        if d.get("type") == "f":
            continue

        # ===== NEW: Preserve original PDF drawing object =====
        path = VectorPath(import_order=import_order)

        colour = d.get("color")
        if colour is None:
            continue

        colour = (
            round(colour[0] * 255),
            round(colour[1] * 255),
            round(colour[2] * 255),
        )

        width = (d.get("width") or 0.0) * PT_TO_MM

        for item in d["items"]:
            command = item[0]

            if command == "l":
                obj = Line(
                    start=make_point(item[1]),
                    end=make_point(item[2]),
                    stroke_color=colour,
                    stroke_width=width,
                    import_order=import_order,
                )
                path.add(obj)
                drawing.add(obj)
                import_order += 1

            elif command == "c":
                obj = Bezier(
                    start=make_point(item[1]),
                    control1=make_point(item[2]),
                    control2=make_point(item[3]),
                    end=make_point(item[4]),
                    stroke_color=colour,
                    stroke_width=width,
                    import_order=import_order,
                )
                path.add(obj)
                drawing.add(obj)
                import_order += 1

            else:
                unsupported[command] = unsupported.get(command, 0) + 1

        # ===== NEW: Store original PDF path =====
        if path.objects:
            drawing.paths.append(path)

    if unsupported:
        print("Unsupported PDF primitives:")
        for k in sorted(unsupported):
            print(f"   {k} : {unsupported[k]}")
        print()

    print()
    print(f"Imported paths : {len(drawing.paths)}")

    for i, path in enumerate(drawing.paths[:20]):

        lines = sum(isinstance(o, Line) for o in path.objects)
        curves = sum(isinstance(o, Bezier) for o in path.objects)

        print(
            f"Path {i+1:2d}: "
            f"{len(path.objects):3d} objects   "
            f"L={lines:2d}   "
            f"C={curves:3d}"
        )

    return drawing


