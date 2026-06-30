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

    import_order = 0

    for d in drawings:

        colour = d.get("color")

        if colour is None:
            colour = (0, 0, 0)

        else:

            colour = (
                round(colour[0] * 255),
                round(colour[1] * 255),
                round(colour[2] * 255),
            )

        width = d.get("width")

        if width is None:
            width = 0.0

        width *= PT_TO_MM

        for item in d["items"]:

            command = item[0]

            # ------------------------------------
            # LINE
            # ------------------------------------

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

            # ------------------------------------
            # BEZIER
            # ------------------------------------

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

            # ------------------------------------
            # UNKNOWN
            # ------------------------------------

            else:

                unsupported[command] = unsupported.get(command, 0) + 1

    if unsupported:

        print("Unsupported PDF primitives:")

        for k in sorted(unsupported):

            print(f"   {k} : {unsupported[k]}")

        print()

    return drawing
