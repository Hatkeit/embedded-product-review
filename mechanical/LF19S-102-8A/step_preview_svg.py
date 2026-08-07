#!/usr/bin/env python3
"""Isometric wireframe preview of a faceted STEP file, as a standalone SVG.

Reads the STEP back through validate_step's parser, collects every unique
undirected edge, and projects it isometrically. Purely a review aid - no CAD
kernel required.

    python3 step_preview_svg.py LF19S-102-8A.step lf19_iso.svg
"""

from __future__ import annotations

import math
import re
import sys
from typing import Dict, Set, Tuple

from validate_step import kind, loop_of, parse, point_of, refs

COS30 = math.cos(math.radians(30.0))
SIN30 = math.sin(math.radians(30.0))

STYLE = {
    "winding": ("#4a5f7a", 0.6),
    "separator": ("#8a6d3b", 0.7),
    "lead": ("#a03c3c", 0.9),
}


def project(p: Tuple[float, float, float]) -> Tuple[float, float]:
    x, y, z = p
    return (x - y) * COS30, (x + y) * SIN30 - z


def group_of(name: str) -> str:
    if name.startswith("lead"):
        return "lead"
    if name.startswith("separator"):
        return "separator"
    return "winding"


def main(src: str, dst: str) -> int:
    ents = parse(src)
    breps = [i for i, b in ents.items() if kind(b) == "MANIFOLD_SOLID_BREP"]

    segs: Dict[str, Set[Tuple[Tuple[float, float], Tuple[float, float]]]] = {
        k: set() for k in STYLE
    }
    for br in breps:
        m = re.match(r"MANIFOLD_SOLID_BREP\('([^']*)'", ents[br])
        grp = group_of(m.group(1) if m else "")
        for face in refs(ents[refs(ents[br])[0]]):
            for a, b in loop_of(ents, face):
                pa, pb = project(point_of(ents, a)), project(point_of(ents, b))
                segs[grp].add((pa, pb) if pa <= pb else (pb, pa))

    allp = [p for s in segs.values() for seg in s for p in seg]
    if not allp:
        print("nothing to draw", file=sys.stderr)
        return 1
    x0, x1 = min(p[0] for p in allp), max(p[0] for p in allp)
    y0, y1 = min(p[1] for p in allp), max(p[1] for p in allp)
    pad = 2.0

    out = [
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="{x0 - pad:.3f} {y0 - pad:.3f} '
        f'{x1 - x0 + 2 * pad:.3f} {y1 - y0 + 2 * pad:.3f}" '
        f'width="760" fill="none" stroke-linecap="round">',
        '<rect x="-1000" y="-1000" width="4000" height="4000" fill="#ffffff"/>',
    ]
    for grp, (colour, width) in STYLE.items():
        if not segs[grp]:
            continue
        out.append(f'<g stroke="{colour}" stroke-width="{width * 0.12:.3f}">')
        for (ax, ay), (bx, by) in sorted(segs[grp]):
            out.append(f'<line x1="{ax:.3f}" y1="{ay:.3f}" x2="{bx:.3f}" y2="{by:.3f}"/>')
        out.append("</g>")
    out.append("</svg>")

    with open(dst, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out) + "\n")
    print(f"wrote {dst} ({sum(len(s) for s in segs.values())} edges)")
    return 0


if __name__ == "__main__":
    a = sys.argv[1] if len(sys.argv) > 1 else "LF19S-102-8A.step"
    b = sys.argv[2] if len(sys.argv) > 2 else "lf19_iso.svg"
    sys.exit(main(a, b))
