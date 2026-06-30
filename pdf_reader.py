import fitz

from drawing import *

# ============================================================
# CONSTANTS
# ============================================================

PT_TO_MM = 25.4 / 72.0

# ============================================================
# HELPERS
# ============================================================

def make_point(pdf_point):
    return Point(
        pdf_point.x * PT_TO_MM,
        pdf_point.y * PT_TO_MM,
    )

# ============================================================
# READER
# ============================================================

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

    # --------------------------------------------------------
    # TEMPORARY DIAGNOSTIC
    # Remove once this PDF issue is solved.
    # --------------------------------------------------------

    print()
    print("=" * 60)

    for i, d in enumerate(drawings):

        if len(d["items"]) > 30:

            print(f"LARGE DRAWING #{i}")
            print("=" * 60)

            for key in sorted(d.keys()):
                print(f"{key}: {d[key]}")

            break

    print()

    import_order = 0

    for d in drawings:

        # Ignore pure fills
        if d.get("type") == "f":
            continue

        colour = d.get("color")

        # No stroke = nothing to laser
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

                drawing.add(
                    Line(
                        start=make_point(item[1]),
                        end=make_point(item[2]),
                        stroke_color=colour,
                        stroke_width=width,
                        import_order=import_order,
                    )
                )

                import_order += 1

            elif command == "c":

                drawing.add(
                    Bezier(
                        start=make_point(item[1]),
                        control1=make_point(item[2]),
                        control2=make_point(item[3]),
                        end=make_point(item[4]),
                        stroke_color=colour,
                        stroke_width=width,
                        import_order=import_order,
                    )
                )

                import_order += 1

            else:

                unsupported[command] = unsupported.get(command, 0) + 1

    if unsupported:

        print("Unsupported PDF primitives:")

        for k in sorted(unsupported):
            print(f"   {k} : {unsupported[k]}")

        print()

    return drawing


