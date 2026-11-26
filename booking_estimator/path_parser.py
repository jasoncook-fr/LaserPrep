"""SVG path-data parser for linear and Bézier commands."""
from __future__ import annotations
import re

TOKEN = re.compile(r"[MmLlHhVvZzCcSsQqTt]|[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?")
COMMANDS = set("MmLlHhVvZzCcSsQqTt")


def parse_path_data(data: str) -> list[dict[str, object]]:
    """Parse M/L/H/V/Z, C/S, and Q/T commands into segment records.

    Coordinates remain in SVG user space. Line, cubic, and quadratic
    segments are represented explicitly; smooth commands reflect the
    preceding curve's final control point when applicable.
    """
    tokens = TOKEN.findall(data or "")
    if not tokens:
        raise ValueError("SVG path data must not be empty")
    cleaned = TOKEN.sub("", data)
    if cleaned.strip(" ,\\t\\r\\n"):
        raise ValueError(f"Unsupported or invalid path syntax: {cleaned!r}")

    segments: list[dict[str, object]] = []
    i = 0
    cmd = None
    current = (0.0, 0.0)
    substart = None
    previous_curve_control = None
    previous_segment_type = None

    def number_pair(index):
        if index + 1 >= len(tokens) or tokens[index] in COMMANDS or tokens[index+1] in COMMANDS:
            raise ValueError("Command requires coordinate pairs")
        return float(tokens[index]), float(tokens[index+1])

    while i < len(tokens):
        if tokens[i] in COMMANDS:
            cmd = tokens[i]
            i += 1
        elif cmd is None:
            raise ValueError("SVG path data must begin with a command")

        if cmd in "Zz":
            if substart is None:
                raise ValueError("Close-path without subpath")
            if current != substart:
                segments.append({"type":"line","start":current,"end":substart,"closed":True})
            current = substart
            cmd = None
            previous_curve_control = None
            previous_segment_type = "line"
            continue

        if cmd in "MmLl":
            x, y = number_pair(i); i += 2
            if cmd.islower(): x += current[0]; y += current[1]
            point = (x, y)
            if cmd in "Mm":
                current = point; substart = point; cmd = "l" if cmd == "m" else "L"
            else:
                segments.append({"type":"line","start":current,"end":point})
                current = point; previous_segment_type="line"; previous_curve_control=None
        elif cmd in "Hh":
            if i >= len(tokens) or tokens[i] in COMMANDS: raise ValueError("H requires a value")
            x=float(tokens[i]); i+=1
            if cmd=="h": x+=current[0]
            point=(x,current[1]); segments.append({"type":"line","start":current,"end":point}); current=point
            previous_segment_type="line"; previous_curve_control=None
        elif cmd in "Vv":
            if i >= len(tokens) or tokens[i] in COMMANDS: raise ValueError("V requires a value")
            y=float(tokens[i]); i+=1
            if cmd=="v": y+=current[1]
            point=(current[0],y); segments.append({"type":"line","start":current,"end":point}); current=point
            previous_segment_type="line"; previous_curve_control=None
        elif cmd in "Cc":
            vals=[]
            for _ in range(3):
                x,y=number_pair(i); i+=2
                if cmd=="c": x+=current[0]; y+=current[1]
                vals.append((x,y))
            control1,control2,end=vals
            segments.append({"type":"cubic","start":current,"control1":control1,"control2":control2,"end":end})
            current=end; previous_curve_control=control2; previous_segment_type="cubic"
        elif cmd in "Ss":
            x,y=number_pair(i); i+=2
            if cmd=="s": x+=current[0]; y+=current[1]
            control2=(x,y)
            control1=(2*current[0]-previous_curve_control[0],2*current[1]-previous_curve_control[1]) if previous_segment_type=="cubic" and previous_curve_control is not None else current
            x,y=number_pair(i); i+=2
            if cmd=="s": x+=current[0]; y+=current[1]
            end=(x,y)
            segments.append({"type":"cubic","start":current,"control1":control1,"control2":control2,"end":end})
            current=end; previous_curve_control=control2; previous_segment_type="cubic"
        elif cmd in "Qq":
            x,y=number_pair(i); i+=2
            if cmd=="q": x+=current[0]; y+=current[1]
            control=(x,y)
            x,y=number_pair(i); i+=2
            if cmd=="q": x+=current[0]; y+=current[1]
            end=(x,y)
            segments.append({"type":"quadratic","start":current,"control":control,"end":end})
            current=end; previous_curve_control=control; previous_segment_type="quadratic"
        elif cmd in "Tt":
            control=(2*current[0]-previous_curve_control[0],2*current[1]-previous_curve_control[1]) if previous_segment_type=="quadratic" and previous_curve_control is not None else current
            x,y=number_pair(i); i+=2
            if cmd=="t": x+=current[0]; y+=current[1]
            end=(x,y)
            segments.append({"type":"quadratic","start":current,"control":control,"end":end})
            current=end; previous_curve_control=control; previous_segment_type="quadratic"
        else:
            raise ValueError(f"Unsupported path command: {cmd}")

    return segments
