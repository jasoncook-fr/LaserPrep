#!/usr/bin/env python3
"""Experimental raster-scan distance estimator using Inkscape PNG rendering.

This is a geometry diagnostic, not a runtime predictor. It rasterizes SVGs to a
temporary bitmap, samples scan rows, and reports estimated raster scan distance.
"""
from __future__ import annotations
import argparse, csv, subprocess, tempfile, sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow is required. Install it in your venv: pip install Pillow", file=sys.stderr)
    raise SystemExit(2)

def render(svg: Path, png: Path, dpi: int):
    cmd=["inkscape",str(svg),f"--export-filename={png}",f"--export-dpi={dpi}"]
    result=subprocess.run(cmd,capture_output=True,text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "Inkscape export failed")

def analyze(svg: Path, dpi: int, pitch_mm: float, threshold: int, direction: str):
    with tempfile.TemporaryDirectory(prefix="svg_fill_scan_") as td:
        png=Path(td)/"render.png"
        render(svg,png,dpi)
        im=Image.open(png).convert("RGBA")
        w,h=im.size
        pix=im.load()
        # Pixel is treated as artwork if sufficiently opaque and sufficiently dark.
        mask=[]
        for y in range(h):
            row=[]
            for x in range(w):
                r,g,b,a=pix[x,y]
                row.append(a >= threshold and (r+g+b)/3 < 250)
            mask.append(row)
        mm_per_px=25.4/dpi
        pitch_px=max(1,round(pitch_mm/mm_per_px))
        scan_rows=list(range(0,h,pitch_px))
        occupied=[]
        pixel_sum=0
        run_sum=0
        for y in scan_rows:
            row=mask[y]
            xs=[x for x,v in enumerate(row) if v]
            if xs:
                occupied.append(y)
                pixel_sum += len(xs)
                # Sum lengths of black pixel runs; diagnostic only.
                inrun=False
                for v in row:
                    if v and not inrun:
                        run_sum += 1; inrun=True
                    elif not v and inrun:
                        inrun=False
                if inrun: pass
        if not occupied:
            return {"file":str(svg),"width_px":w,"height_px":h,"occupied_scan_rows":0,
                    "sample_pitch_mm":pitch_mm,"raster_bbox_distance_mm":0,
                    "active_pixel_length_mm":0,"run_count":0,"warnings":"No dark opaque pixels detected"}
        # Typical raster engraving scans across the complete bounding width of each occupied row.
        bbox_width_mm=w*mm_per_px
        full_scan_distance=bbox_width_mm*len(occupied)
        # Pixel count per sampled row, converted to pixel length; this ignores laser off travel.
        active_length=pixel_sum*mm_per_px
        return {"file":str(svg),"width_px":w,"height_px":h,"occupied_scan_rows":len(occupied),
                "sample_pitch_mm":pitch_mm,"raster_bbox_distance_mm":full_scan_distance,
                "active_pixel_length_mm":active_length,"run_count":run_sum,
                "warnings":"Rasterized appearance includes rendered strokes and fills; SVG processing/color semantics not separated."}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("svg_files",nargs="+",type=Path)
    ap.add_argument("--dpi",type=int,default=300,help="Render resolution (default 300)")
    ap.add_argument("--pitch-mm",type=float,default=0.1,help="Sampling interval between scan rows in mm (default 0.1)")
    ap.add_argument("--threshold",type=int,default=16,help="Alpha threshold 0-255 (default 16)")
    ap.add_argument("--csv",type=Path,help="Optional CSV output")
    args=ap.parse_args()
    if args.dpi<=0 or args.pitch_mm<=0:
        ap.error("dpi and pitch-mm must be positive")
    rows=[]
    for svg in args.svg_files:
        if not svg.exists():
            print(f"ERROR: missing file: {svg}",file=sys.stderr); continue
        try:
            r=analyze(svg,args.dpi,args.pitch_mm,args.threshold,"ltr"); rows.append(r)
            print(f"\n{svg.name}")
            print(f"  rendered: {r['width_px']} x {r['height_px']} px @ {args.dpi} DPI")
            print(f"  occupied sampled scan rows: {r['occupied_scan_rows']} (pitch {args.pitch_mm:g} mm)")
            print(f"  estimated full-width raster distance: {r['raster_bbox_distance_mm']:,.1f} mm")
            print(f"  active-pixel length proxy: {r['active_pixel_length_mm']:,.1f} mm")
            print(f"  detected scanline runs: {r['run_count']:,}")
            print(f"  WARNING: {r['warnings']}")
        except Exception as e:
            print(f"ERROR processing {svg}: {e}",file=sys.stderr)
    if args.csv and rows:
        args.csv.parent.mkdir(parents=True,exist_ok=True)
        with args.csv.open("w",newline="",encoding="utf-8") as f:
            writer=csv.DictWriter(f,fieldnames=list(rows[0]))
            writer.writeheader(); writer.writerows(rows)
        print(f"\nCSV saved: {args.csv}")
    return 0 if rows else 1
if __name__=="__main__":
    raise SystemExit(main())
