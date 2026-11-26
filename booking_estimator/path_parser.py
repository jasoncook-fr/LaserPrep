"""Initial SVG path-data parser: linear commands and closure only."""
from __future__ import annotations
import re

TOKEN = re.compile(r"[MmLlHhVvZz]|[+-]?(?:\\d+(?:\\.\\d*)?|\\.\\d+)(?:[eE][+-]?\\d+)?")
COMMANDS = set("MmLlHhVvZz")

def parse_path_data(data: str) -> list[dict[str, object]]:
    """Parse M/L/H/V/Z path data into line-segment records.

    Segment entries contain start/end tuples; close-path entries are marked
    closed=True. Curves and arcs are deliberately unsupported in this stage.
    """
    tokens = TOKEN.findall(data or "")
    if "".join(tokens).replace(" ", "") == "" and data.strip():
        raise ValueError("Invalid SVG path data")
    # Ensure no unrecognized text is silently skipped.
    cleaned = TOKEN.sub("", data)
    if cleaned.strip(" ,\\t\\r\\n"):
        raise ValueError(f"Unsupported or invalid path syntax: {cleaned!r}")
    segments: list[dict[str, object]] = []
    i = 0; cmd = None; current=(0.0,0.0); substart=None
    while i < len(tokens):
        if tokens[i] in COMMANDS:
            cmd=tokens[i]; i+=1
        elif cmd is None:
            raise ValueError("SVG path data must begin with a command")
        if cmd in "Zz":
            if substart is None: raise ValueError("Close-path without subpath")
            if current != substart:
                segments.append({"type":"line","start":current,"end":substart,"closed":True})
            current=substart; cmd=None; continue
        if cmd in "MmLl":
            if i+1>=len(tokens) or tokens[i] in COMMANDS or tokens[i+1] in COMMANDS:
                raise ValueError(f"Command {cmd} requires coordinate pairs")
            x=float(tokens[i]); y=float(tokens[i+1]); i+=2
            if cmd.islower(): x+=current[0]; y+=current[1]
            point=(x,y)
            if cmd in "Mm":
                current=point; substart=point
                # Subsequent coordinate pairs after moveto are lineto.
                cmd="l" if cmd=="m" else "L"
            else:
                segments.append({"type":"line","start":current,"end":point})
                current=point
        elif cmd in "Hh":
            if i>=len(tokens) or tokens[i] in COMMANDS: raise ValueError("H requires a value")
            x=float(tokens[i]); i+=1
            if cmd=="h": x+=current[0]
            point=(x,current[1]); segments.append({"type":"line","start":current,"end":point}); current=point
        elif cmd in "Vv":
            if i>=len(tokens) or tokens[i] in COMMANDS: raise ValueError("V requires a value")
            y=float(tokens[i]); i+=1
            if cmd=="v": y+=current[1]
            point=(current[0],y); segments.append({"type":"line","start":current,"end":point}); current=point
        else:
            raise ValueError(f"Unsupported path command: {cmd}")
    return segments
