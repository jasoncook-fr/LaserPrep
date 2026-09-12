"""
report.py
"""
from pathlib import Path
from datetime import datetime

class Report:
    def __init__(self):
        self.project = ""
        self.generated = datetime.now()
        self.files = []
        self.current = None

    def _ensure(self):
        if self.current is None:
            self.current = {
                "name":"Unknown",
                "objects":0,
                "status":"PASS",
                "warnings":[],
                "alerts":[],
                "repairs":[]
            }

    def begin_file(self, filename):
        if self.current:
            self.files.append(self.current)
        self.current = {
            "name": filename,
            "objects":0,
            "status":"PASS",
            "warnings":[],
            "alerts":[],
            "repairs":[]
        }

    def validation(self,drawing,rotated,overflow,large_ok,small_ok):
        self._ensure()
        if not large_ok:
            self.current["status"]="REJECTED"
            self.current["alerts"].append("Does not fit on large laser.")
        elif not small_ok:
            if self.current["status"]=="PASS":
                self.current["status"]="WARNING"
            self.current["warnings"].append(f"Does not fit on small laser ({overflow:.2f} mm overflow).")

    def complexity(self,c):
        self._ensure()
        self.current["objects"]=c.object_count
        if c.should_abort:
            self.current["status"]="REJECTED"
            self.current["alerts"].append("Complexity exceeds supported limit.")

    def geometry(self,g):
        self._ensure()
        if getattr(g,"tiny_lines",0):
            self.current["warnings"].append(f"{g.tiny_lines} tiny segments detected.")

    def suspicious_scale(self, drawing, object_count):
        self._ensure()

        self.current["status"] = (
            "WARNING"
            if self.current["status"] == "PASS"
            else self.current["status"]
        )

        self.current["warnings"].append(
            f"⚠️ Suspicious scale: "
            f"drawing is {drawing.drawing_width:.2f} × "
            f"{drawing.drawing_height:.2f} mm "
            f"with {object_count} vector objects. "
            "This may indicate an incorrect PDF export scale. "
            "Please verify the original drawing size."
        )

    def colours(self, colors):
        self._ensure()

        if colors.unsupported:

            self.current["status"] = "REJECTED"

            for rgb, count in sorted(colors.unsupported.items()):

                colour = "#{:02X}{:02X}{:02X}".format(*rgb)

                self.current["alerts"].append(
                    f"Unsupported colour {colour} "
                    f"({count} objects)."
                )

    def cleanup(self,zero,dup,col):
        self._ensure()
        if zero:
            self.current["repairs"].append(f"Removed {zero} zero-length lines")
        if dup:
            self.current["repairs"].append(f"Removed {dup} duplicate lines")
        if col:
            self.current["repairs"].append(f"Corrected {col} colours")

    def statistics(self,s):
        pass

    def chains(self,c):
        pass

    def save(self,path,project):
        if self.current:
            self.files.append(self.current)
            self.current=None

        total_objects=sum(f["objects"] for f in self.files)

        rejected=sum(f["status"]=="REJECTED" for f in self.files)
        warnings=sum(bool(f["warnings"]) for f in self.files)
        passed=sum(f["status"]=="PASS" and not f["warnings"] for f in self.files)

        out=[]
        out.append("="*60)
        out.append("LASERPREP OPERATOR REPORT")
        out.append("="*60)
        out.append(f"Project        : {project}")
        out.append(f"Generated      : {self.generated:%Y-%m-%d %H:%M:%S}")
        out.append(f"Files          : {len(self.files)}")
        out.append(f"Vector objects : {total_objects}")
        out.append("")
        out.append("SUMMARY")
        out.append("-"*60)
        out.append(f"🟢 Accepted : {passed}")
        out.append(f"🟡 Warnings : {warnings}")
        out.append(f"🔴 Rejected : {rejected}")

        alerts=[(f["name"],a) for f in self.files for a in f["alerts"]]
        warns=[(f["name"],w) for f in self.files for w in f["warnings"]]
        repairs=[(f["name"],r) for f in self.files for r in f["repairs"]]

        if alerts:
            out.extend(["","ALERTS","-"*60])
            for n,a in alerts:
                out.append(f"{n}: {a}")

        if warns:
            out.extend(["","WARNINGS","-"*60])
            for n,w in warns:
                out.append(f"{n}: {w}")

        if repairs:
            out.extend(["","AUTOMATIC REPAIRS","-"*60])
            for n,r in repairs:
                out.append(f"{n}: {r}")

        out.extend(["","FILES","-"*60])
        for f in self.files:
            icon = {
                "PASS": "✅",
                "WARNING": "⚠️",
                "REJECTED": "❌",
            }[f["status"]]
            out.append(f"{icon} {f['name']} ({f['objects']} objects)")

        Path(path).write_text("\n".join(out),encoding="utf-8")


