from drawing import Line, Bezier


MARGIN_MM = 5.0


def _bbox_of_points(points):

    xs = [p.x for p in points]
    ys = [p.y for p in points]

    return (
        min(xs),
        min(ys),
        max(xs),
        max(ys),
    )


def _bbox_of_path(path):

    pts = []

    for obj in path:

        if isinstance(obj, Line):

            pts.append(obj.start)
            pts.append(obj.end)

        elif isinstance(obj, Bezier):

            pts.append(obj.start)
            pts.append(obj.control1)
            pts.append(obj.control2)
            pts.append(obj.end)

    if not pts:
        return None

    return _bbox_of_points(pts)


def _expand(box, margin):

    return (
        box[0] - margin,
        box[1] - margin,
        box[2] + margin,
        box[3] + margin,
    )


def _intersects(a, b):

    return not (

        a[2] < b[0]
        or
        a[0] > b[2]
        or
        a[3] < b[1]
        or
        a[1] > b[3]

    )


def filter_text_groups(drawing):

    #
    # Collect geometry boxes.
    #

    geometry_boxes = []

    for path in drawing.objects:

        if getattr(path, "is_text", False):
            continue

        box = _bbox_of_path(path)

        if box is not None:
            geometry_boxes.append(_expand(box, MARGIN_MM))

    #
    # Group text.
    #

    groups = {}

    for path in drawing.objects:

        if not getattr(path, "is_text", False):
            continue

        gid = getattr(path, "group_id", None)

        if gid is None:
            continue

        groups.setdefault(gid, []).append(path)

    #
    # Decide which groups survive.
    #

    keep = set()

    for gid, paths in groups.items():

        #
        # Union bounding box.
        #

        boxes = [_bbox_of_path(p) for p in paths]

        boxes = [b for b in boxes if b is not None]

        if not boxes:
            continue

        left = min(b[0] for b in boxes)
        top = min(b[1] for b in boxes)
        right = max(b[2] for b in boxes)
        bottom = max(b[3] for b in boxes)

        text_box = (left, top, right, bottom)

        for geo in geometry_boxes:

            if _intersects(text_box, geo):

                keep.add(gid)
                break

    #
    # Filter.
    #

    drawing.objects = [

        p

        for p in drawing.objects

        if (
            not getattr(p, "is_text", False)
            or
            getattr(p, "group_id", None) in keep
        )

    ]
