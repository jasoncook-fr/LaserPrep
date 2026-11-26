"""Affine transformation pipeline."""
from .geometry import Matrix, Point

def transform_vector(matrix: Matrix, vector: Point) -> Point:
    return Point(matrix.a*vector.x + matrix.c*vector.y, matrix.b*vector.x + matrix.d*vector.y)

def determinant(matrix: Matrix) -> float:
    return matrix.a*matrix.d - matrix.b*matrix.c

def inverse(matrix: Matrix) -> Matrix:
    det = determinant(matrix)
    if det == 0:
        raise ValueError("Cannot invert singular matrix")
    a,b,c,d = matrix.d/det,-matrix.b/det,-matrix.c/det,matrix.a/det
    return Matrix(a,b,c,d,-(a*matrix.e+c*matrix.f),-(b*matrix.e+d*matrix.f))

def transform_segment(matrix: Matrix, segment: dict[str, object]) -> dict[str, object]:
    kind=segment.get("type")
    keys={"line":("start","end"),"quadratic":("start","control","end"),"cubic":("start","control1","control2","end")}
    if kind == "arc":
        return {"type":"transformed_arc","segment":dict(segment),"matrix":matrix}
    if kind not in keys:
        raise ValueError(f"Unsupported segment type: {kind!r}")
    result=dict(segment)
    for key in keys[kind]:
        value=segment.get(key)
        if value is not None:
            p=matrix.apply(Point(float(value[0]),float(value[1])))
            result[key]=(p.x,p.y)
    return result

def transform_segments(matrix: Matrix, segments):
    return [transform_segment(matrix,s) for s in segments]
