"""
report.py
"""
from pathlib import Path
from datetime import datetime

class Report:
    def __init__(self):
        self.lines=[]

    def section(self,name):
        self.lines.extend(["",name,"-"*37])

    def line(self,label,value):
        self.lines.append(f"{label:<18} : {value}")

    def validation(self,drawing,rotated,overflow,large_ok,small_ok):
        self.section("Validation")
        self.line("Drawing Size",f"{drawing.drawing_width:.2f} × {drawing.drawing_height:.2f} mm")
        self.line("Orientation","Rotated" if rotated else "Original")
        self.line("Overflow",f"{overflow:.2f} mm")
        self.line("Large Laser","✓ YES" if large_ok else "✗ NO")
        self.line("Small Laser","✓ YES" if small_ok else "✗ NO")

    def complexity(self,c):
        self.section("Complexity Analysis")
        self.line("Vector objects",c.object_count)
        self.line("Complexity rating",c.rating)
        if c.should_abort:
            self.lines.extend(["","ALERT","-"*37,
            "This drawing exceeds the maximum",
            "complexity supported by LaserPrep.","",
            "Processing cancelled."])

    def geometry(self,g):
        self.section("Geometry")
        self.line("Zero-length lines",g.zero_length_lines)
        self.line("Tiny segments",g.tiny_lines)
        self.line("Duplicate lines",g.duplicate_lines)
        if g.shortest_line_mm is not None:
            self.line("Shortest segment",f"{g.shortest_line_mm:.6f} mm")

    def colours(self,colors):
        self.section("Colours")
        for n,cnt in colors.official.items():
            if cnt:self.lines.append(f"{n:<10} : {cnt}")
        if colors.near:
            self.section("Near Official Colours")
            for rgb,info in sorted(colors.near.items()):
                self.lines.append(f"{rgb} -> {info['target']} : {info['count']}")
        if colors.unsupported:
            self.section("Unsupported Colours")
            for rgb,cnt in sorted(colors.unsupported.items()):
                self.lines.append(f"{rgb} : {cnt}")

    def cleanup(self,a,b,c):
        self.section("Cleanup")
        self.line("Removed zero-length",a)
        self.line("Removed duplicates",b)
        self.line("Colours corrected",c)

    def statistics(self,s):
        self.section("Geometry Statistics")
        for lab,val in [("Total lines",s.total_lines),("< 0.01 mm",s.lt_001),("0.01-0.05 mm",s.lt_005),("0.05-0.10 mm",s.lt_010),("0.10-0.50 mm",s.lt_050),("0.50-1.00 mm",s.lt_100),("> 1.00 mm",s.gt_100)]:
            self.line(lab,val)

    def chains(self,ch):
        self.section("Geometry Chains")
        self.line("Total chains",ch.total_chains)
        self.line("Longest chain",ch.longest_chain)
        avg=ch.total_segments/ch.total_chains if ch.total_chains else 0
        self.line("Average chain",f"{avg:.1f}")
        self.lines.extend(["","Distribution"])
        for lab,val in [("1 segment",ch.one),("2 - 5 segments",ch.two_to_five),("6 - 20 segments",ch.six_to_twenty),("21 - 100 segments",ch.twentyone_to_hundred),("> 100 segments",ch.over_hundred)]:
            self.line(lab,val)

    def save(self,path,project):
        header=[
        "="*60,"LASERPREP REPORT","="*60,
        f"Project : {project}",
        f"Generated : {datetime.now():%Y-%m-%d %H:%M:%S}",""]
        Path(path).write_text("\n".join(header+self.lines),encoding="utf-8")


