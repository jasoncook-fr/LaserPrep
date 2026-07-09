import fitz
from drawing import Drawing, Point, Line, Bezier
from vector_path import VectorPath

PT_TO_MM = 25.4 / 72.0

def make_point(pdf_point):
    return Point(pdf_point.x * PT_TO_MM, pdf_point.y * PT_TO_MM)

def pdf_colour_to_rgb(c):
    if c is None:
        return None
    return (round(c[0]*255), round(c[1]*255), round(c[2]*255))

def rectangle_to_lines(rect, colour, width, order):
    p1 = Point(rect.x0*PT_TO_MM, rect.y0*PT_TO_MM)
    p2 = Point(rect.x1*PT_TO_MM, rect.y0*PT_TO_MM)
    p3 = Point(rect.x1*PT_TO_MM, rect.y1*PT_TO_MM)
    p4 = Point(rect.x0*PT_TO_MM, rect.y1*PT_TO_MM)
    return [
        Line(p1,p2,colour,width,order),
        Line(p2,p3,colour,width,order+1),
        Line(p3,p4,colour,width,order+2),
        Line(p4,p1,colour,width,order+3),
    ]

def read_pdf(filename):
    doc = fitz.open(filename)
    page = doc[0]
    drawing = Drawing(
        name=filename.stem,
        width=page.rect.width*PT_TO_MM,
        height=page.rect.height*PT_TO_MM,
    )
    unsupported={}
    import_order=0
    for d in page.get_drawings():
        stroke=pdf_colour_to_rgb(d.get("color"))
        fill=pdf_colour_to_rgb(d.get("fill"))
        width=(d.get("width") or 0.0)*PT_TO_MM
        path=VectorPath(
            stroke_color=stroke,
            fill_color=fill,
            stroke_width=width,
            stroke_enabled=stroke is not None,
            fill_enabled=False,
            import_order=import_order,
        )
        for item in d.get("items",[]):
            cmd=item[0]
            if cmd=="l":
                obj=Line(make_point(item[1]),make_point(item[2]),stroke,width,import_order)
                path.add(obj); drawing.add(obj); import_order+=1
            elif cmd=="c":
                obj=Bezier(make_point(item[1]),make_point(item[2]),make_point(item[3]),make_point(item[4]),stroke,width,import_order)
                path.add(obj); drawing.add(obj); import_order+=1
            elif cmd=="re":
                for obj in rectangle_to_lines(item[1],stroke,width,import_order):
                    path.add(obj); drawing.add(obj)
                path.close()
                import_order+=4
            else:
                unsupported[cmd]=unsupported.get(cmd,0)+1
        if not path.is_empty:
            drawing.paths.append(path)
    if unsupported:
        print("Unsupported PDF primitives:")
        for k in sorted(unsupported):
            print(f"   {k}: {unsupported[k]}")
    drawing.pdf_statistics = {
        "paths": len(drawing.paths),
        "objects": len(drawing.objects),
        "unsupported": unsupported.copy(),
    }
    return drawing


