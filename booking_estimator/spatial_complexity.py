"""Spatial distribution and local geometry density analysis (Stage 12).

Features are descriptive only: SVG element bounding boxes are not actual path
coverage footprints and are used as a coarse spatial proxy.
"""
import math

def analyze_spatial_complexity(measurement: dict, grid_size: int = 4) -> dict:
    if not isinstance(grid_size, int) or grid_size < 1 or grid_size > 64:
        raise ValueError("grid_size must be an integer between 1 and 64")
    elements=measurement.get("elements", [])
    width=float(measurement.get("width_mm",0) or 0); height=float(measurement.get("height_mm",0) or 0)
    min_x=float(measurement.get("min_x_mm",0) or 0); min_y=float(measurement.get("min_y_mm",0) or 0)
    cells=[[0.0 for _ in range(grid_size)] for _ in range(grid_size)]
    counts=[[0 for _ in range(grid_size)] for _ in range(grid_size)]
    if width>0 and height>0:
        for e in elements:
            length=float(e.get("length_mm",0) or 0)
            cx=float(e.get("min_x_mm",min_x) or min_x)+float(e.get("width_mm",0) or 0)/2
            cy=float(e.get("min_y_mm",min_y) or min_y)+float(e.get("height_mm",0) or 0)/2
            ix=max(0,min(grid_size-1,int((cx-min_x)/width*grid_size)))
            iy=max(0,min(grid_size-1,int((cy-min_y)/height*grid_size)))
            cells[iy][ix]+=length; counts[iy][ix]+=1
    vals=[v for row in cells for v in row]; occupied=sum(v>0 for v in vals); total=sum(vals)
    mean=total/len(vals) if vals else 0; variance=sum((v-mean)**2 for v in vals)/len(vals) if vals else 0
    entropy=sum(-(v/total)*math.log(v/total) for v in vals if v>0) if total>0 else 0
    max_cell=max(vals,default=0)
    return {"spatial_version":1,"grid_size":grid_size,"grid_length_mm":cells,"grid_element_count":counts,
        "occupied_cells":occupied,"occupied_cell_fraction":occupied/len(vals) if vals else 0,
        "length_per_cell_mean_mm":mean,"length_per_cell_variance_mm2":variance,
        "max_cell_length_mm":max_cell,"max_cell_fraction_of_total":max_cell/total if total else 0,
        "spatial_entropy":entropy,"spatial_entropy_normalized":entropy/math.log(len(vals)) if total and len(vals)>1 else 0,
        "document_bbox_area_mm2":width*height,"geometry_density_mm_per_mm2":total/(width*height) if width*height>0 else 0,
        "total_length_mm":total,"coverage_complete":bool(measurement.get("coverage_complete",False)),
        "coverage_status":measurement.get("coverage_status","unknown")}
